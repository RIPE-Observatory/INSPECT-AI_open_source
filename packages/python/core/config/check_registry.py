"""
Dynamic Check Registry for INSPECT-AI

This module provides configuration-driven check management, allowing different
deployment profiles (beta, full production, etc.) to enable/disable checks
without code changes.

The registry:
- Loads check configuration from checks_registry.yaml
- Determines which checks are enabled based on environment profile
- Dynamically imports only enabled check tasks (no dead code loading)
- Provides metadata for frontend rendering and orchestration
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import yaml

logger = logging.getLogger(__name__)


class CheckConfig:
    """Configuration for a single check."""

    def __init__(self, check_id: str, config: Dict[str, Any]):
        self.id = check_id
        self.display_name = config["display_name"]
        self.description = config["description"]
        self.check_number = config["check_number"]
        self.inspect_sr_mapping = config.get("inspect_sr_mapping", "")
        self.task_name = config["task_name"]
        self.queue = config.get("queue", "default")
        self.timeout = config.get("timeout")
        self.max_tries = config.get("max_tries", 3)
        self.dependencies = config.get("dependencies", [])
        self.phase = config.get("phase", 1)
        self.executor = config.get("executor", "inline")

    def __repr__(self):
        return f"<CheckConfig(id={self.id}, number={self.check_number}, phase={self.phase})>"


class CheckRegistry:
    """
    Central registry for all INSPECT-AI checks.

    Usage:
        from core.config.check_registry import registry

        # Get enabled checks
        enabled = registry.get_enabled_checks()

        # Get ARQ task functions (only imports enabled checks)
        tasks = registry.get_arq_task_functions()

        # Get check count for UI
        total = registry.get_total_checks()
    """

    def __init__(self, config_path: Optional[Path] = None, profile: Optional[str] = None):
        """
        Initialize the check registry.

        Args:
            config_path: Path to checks_registry.yaml (defaults to same directory)
            profile: Environment profile. Defaults to env var CHECKS_PROFILE.
        """
        if config_path is None:
            config_path = Path(__file__).parent / "checks_registry.yaml"

        with open(config_path, "r") as f:
            self.raw_config = yaml.safe_load(f)

        # Determine active profile
        self.profile = profile or os.getenv("CHECKS_PROFILE", "beta_inspect_sr")

        # Validate profile exists
        if self.profile not in self.raw_config.get("profiles", {}):
            logger.warning(
                f"Profile '{self.profile}' not found in registry. Falling back to 'beta_inspect_sr'."
            )
            self.profile = "beta_inspect_sr"

        logger.info(f"CheckRegistry initialized with profile: {self.profile}")

        # Load check configurations
        self.all_checks = self._load_all_checks()
        self.enabled_check_ids = self._get_enabled_check_ids()
        self.enabled_checks = self._filter_enabled_checks()
        self._validate_dependencies()
        self._execution_order = self._compute_execution_order()

        logger.info(
            f"Loaded {len(self.enabled_checks)}/{len(self.all_checks)} enabled checks: "
            f"{list(self.enabled_checks.keys())}"
        )

    def _load_all_checks(self) -> Dict[str, CheckConfig]:
        """Load all check configurations from YAML."""
        all_checks = {}
        for check_id, config in self.raw_config.get("checks", {}).items():
            all_checks[check_id] = CheckConfig(check_id, config)
        return all_checks

    def _get_enabled_check_ids(self) -> Set[str]:
        """Get list of enabled check IDs based on active profile."""
        profile_config = self.raw_config["profiles"][self.profile]
        return set(profile_config.get("enabled_checks", []))

    def get_all_check_ids(self) -> Set[str]:
        """Return IDs for all defined checks."""
        return set(self.all_checks.keys())

    def _filter_enabled_checks(self) -> Dict[str, CheckConfig]:
        """Filter checks to only those enabled in the current profile."""
        enabled = {}
        for check_id in self.enabled_check_ids:
            if check_id in self.all_checks:
                enabled[check_id] = self.all_checks[check_id]
            else:
                logger.warning(
                    f"Check '{check_id}' enabled in profile but not defined in checks section"
                )
        return enabled

    def is_enabled(self, check_id: str) -> bool:
        """Check if a specific check is enabled."""
        return check_id in self.enabled_checks

    def get_enabled_checks(self) -> Dict[str, CheckConfig]:
        """Get all enabled checks as CheckConfig objects."""
        return self.enabled_checks

    def get_check(self, check_id: str) -> Optional[CheckConfig]:
        """Get configuration for a specific check."""
        return self.enabled_checks.get(check_id)

    def get_total_checks(self) -> int:
        """Get total number of enabled checks (for UI progress tracking)."""
        return len(self.enabled_checks)

    def get_checks_by_phase(self, phase: int) -> List[CheckConfig]:
        """Get all enabled checks in a specific execution phase."""
        return [
            check for check in self.enabled_checks.values() if check.phase == phase
        ]

    def get_execution_order(self) -> List[CheckConfig]:
        """Return enabled checks in dependency-respecting order."""
        return list(self._execution_order)

    def _validate_dependencies(self) -> None:
        """Ensure enabled checks have valid dependencies."""
        for check in self.enabled_checks.values():
            missing = [
                dep for dep in check.dependencies if dep not in self.enabled_checks
            ]
            if missing:
                logger.warning(
                    "Check '%s' has dependencies not enabled in profile '%s': %s",
                    check.id,
                    self.profile,
                    missing,
                )

    def _compute_execution_order(self) -> List[CheckConfig]:
        """Topologically sort enabled checks respecting phases."""
        order: List[CheckConfig] = []
        resolved: Set[str] = set()
        pending: Dict[str, CheckConfig] = dict(self.enabled_checks)

        while pending:
            ready: List[CheckConfig] = [
                cfg
                for cfg in pending.values()
                if all(dep in resolved for dep in cfg.dependencies)
            ]
            if not ready:
                unresolved = ", ".join(sorted(pending.keys()))
                raise ValueError(
                    f"Circular or unsatisfied dependencies among enabled checks: {unresolved}"
                )

            ready.sort(key=lambda cfg: (cfg.phase, cfg.id))
            for cfg in ready:
                order.append(cfg)
                resolved.add(cfg.id)
                pending.pop(cfg.id, None)

        return order

    def get_arq_task_functions_for_queue(self, queue_name: str) -> List:
        """
        Return ARQ task functions filtered for a specific queue.

        Orchestrator queue is treated specially and only receives the
        `run_evidence_synthesis_arq_task`. Other queues receive the arq
        tasks associated with enabled checks whose queue matches.
        """
        from arq.worker import func
        functions = []

        # Special-case orchestrator queue
        if queue_name in {"arq:queue:orchestrator", "orchestrator"}:
            from core.tasks.arq_tasks import run_evidence_synthesis_arq_task

            functions.append(
                func(run_evidence_synthesis_arq_task, timeout=120, max_tries=3)
            )
            return functions

        # Dynamically import only enabled check tasks
        for check_id, check_config in self.enabled_checks.items():
            if str(check_config.queue) != queue_name:
                continue
            if str(check_config.executor).lower() != "arq":
                continue
            if str(check_config.executor).lower() != "arq":
                continue
            try:
                if check_id == "trial_llm_extraction":
                    from core.tasks.arq_tasks import task_trial_llm_extraction

                    functions.append(
                        func(
                            task_trial_llm_extraction,
                            timeout=check_config.timeout,
                            max_tries=check_config.max_tries,
                        )
                    )

                elif check_id == "timeline_consistency":
                    from core.tasks.arq_tasks import task_timeline_consistency

                    functions.append(
                        func(
                            task_timeline_consistency,
                            timeout=check_config.timeout,
                            max_tries=check_config.max_tries,
                        )
                    )

                elif check_id == "grobid_metadata":
                    from core.tasks.arq_tasks import task_grobid_metadata

                    functions.append(
                        func(
                            task_grobid_metadata,
                            timeout=check_config.timeout,
                            max_tries=check_config.max_tries,
                        )
                    )

                else:
                    logger.warning(
                        "No ARQ function mapping defined for check '%s' (executor=%s)",
                        check_id,
                        check_config.executor,
                    )

            except ImportError as e:
                logger.error(
                    f"Failed to import task for check '{check_id}': {e}. "
                    f"This check will be skipped."
                )

        logger.info(
            "Registered %s ARQ task functions for queue '%s'",
            len(functions),
            queue_name,
        )
        return functions

    def get_queue_config(self, queue_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific queue."""
        return self.raw_config.get("queues", {}).get(queue_name)

    def to_dict(self) -> Dict[str, Any]:
        """
        Export registry as dictionary for API responses.

        Useful for frontend to know which checks are available.
        """
        return {
            "profile": self.profile,
            "total_checks": self.get_total_checks(),
            "checks": {
                check_id: {
                    "display_name": check.display_name,
                    "description": check.description,
                    "check_number": check.check_number,
                    "inspect_sr_mapping": check.inspect_sr_mapping,
                    "phase": check.phase,
                    "dependencies": check.dependencies,
                }
                for check_id, check in self.enabled_checks.items()
            },
        }


# Singleton instance - initialized once at module import
# Environment variable CHECKS_PROFILE determines which checks are loaded
registry = CheckRegistry()


# Convenience function for external use
def get_registry() -> CheckRegistry:
    """Get the singleton check registry instance."""
    return registry

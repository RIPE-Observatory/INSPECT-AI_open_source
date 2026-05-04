"""
Robust GROBID TEI XML Parser

This parser extracts bibliographic metadata from GROBID-processed PDFs
that output TEI XML format. It handles variations and missing data gracefully.
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
import re


class GrobidTEIParser:
    """Robust parser for GROBID TEI XML files"""

    def __init__(self):
        # TEI namespace
        self.ns = {"tei": "http://www.tei-c.org/ns/1.0"}

    def parse_file(self, xml_path: str) -> Dict[str, Any]:
        """Parse a GROBID TEI XML file and extract metadata"""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            return self._parse_root(root)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML file: {e}")
        except Exception as e:
            raise ValueError(f"Error parsing file {xml_path}: {e}")

    def parse_string(self, xml_content: str) -> Dict[str, Any]:
        """Parse XML content string"""
        try:
            root = ET.fromstring(xml_content)
            return self._parse_root(root)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML content: {e}")

    def _parse_root(self, root: ET.Element) -> Dict[str, Any]:
        """Parse the root TEI element"""
        metadata = {
            "title": None,
            "doi": None,
            "journal": None,
            "journal_abbrev": None,
            "publisher": None,
            "volume": None,
            "issue": None,
            "pages": None,
            "page_from": None,
            "page_to": None,
            "publication_date": None,
            "issn": None,
            "eissn": None,
            "authors": [],
            "affiliations": [],
        }

        # Extract basic bibliographic information
        self._extract_title(root, metadata)
        self._extract_doi(root, metadata)
        self._extract_journal_info(root, metadata)
        self._extract_publisher(root, metadata)
        self._extract_publication_details(root, metadata)
        self._extract_identifiers(root, metadata)

        # Extract affiliations first to build index, then extract authors
        affiliation_index = self._extract_affiliations(root, metadata)
        self._extract_authors(root, metadata, affiliation_index)

        return metadata

    def _extract_title(self, root: ET.Element, metadata: Dict[str, Any]) -> None:
        """Extract main title"""
        title_elem = root.find('.//tei:title[@level="a"][@type="main"]', self.ns)
        if title_elem is not None and title_elem.text:
            metadata["title"] = title_elem.text.strip()

    def _extract_doi(self, root: ET.Element, metadata: Dict[str, Any]) -> None:
        """Extract DOI"""
        doi_elem = root.find('.//tei:idno[@type="DOI"]', self.ns)
        if doi_elem is not None and doi_elem.text:
            metadata["doi"] = doi_elem.text.strip()

    def _extract_journal_info(self, root: ET.Element, metadata: Dict[str, Any]) -> None:
        """Extract journal name and abbreviation"""
        journal_elem = root.find('.//tei:title[@level="j"][@type="main"]', self.ns)
        if journal_elem is not None and journal_elem.text:
            metadata["journal"] = journal_elem.text.strip()

        journal_abbrev_elem = root.find(
            './/tei:title[@level="j"][@type="abbrev"]', self.ns
        )
        if journal_abbrev_elem is not None and journal_abbrev_elem.text:
            metadata["journal_abbrev"] = journal_abbrev_elem.text.strip()

    def _extract_publisher(self, root: ET.Element, metadata: Dict[str, Any]) -> None:
        """Extract publisher"""
        publisher_elem = root.find(".//tei:publisher", self.ns)
        if publisher_elem is not None and publisher_elem.text:
            metadata["publisher"] = publisher_elem.text.strip()

    def _extract_publication_details(
        self, root: ET.Element, metadata: Dict[str, Any]
    ) -> None:
        """Extract volume, issue, pages, and publication date"""
        # Volume
        volume_elem = root.find('.//tei:biblScope[@unit="volume"]', self.ns)
        if volume_elem is not None and volume_elem.text:
            metadata["volume"] = volume_elem.text.strip()

        # Issue
        issue_elem = root.find('.//tei:biblScope[@unit="issue"]', self.ns)
        if issue_elem is not None and issue_elem.text:
            metadata["issue"] = issue_elem.text.strip()

        # Pages
        page_elem = root.find('.//tei:biblScope[@unit="page"]', self.ns)
        if page_elem is not None:
            # Check for page range attributes first (more structured)
            page_from = page_elem.get("from")
            page_to = page_elem.get("to")
            if page_from:
                metadata["page_from"] = page_from.strip()
            if page_to:
                metadata["page_to"] = page_to.strip()

            # Use structured range if available, otherwise fall back to text content
            if page_from and page_to:
                metadata["pages"] = f"{page_from}-{page_to}"
            elif page_elem.text:
                metadata["pages"] = page_elem.text.strip()

        # Publication date
        date_elem = root.find('.//tei:date[@type="published"]', self.ns)
        if date_elem is not None:
            # Try 'when' attribute first (ISO format)
            date_when = date_elem.get("when")
            if date_when:
                metadata["publication_date"] = date_when.strip()
            elif date_elem.text:
                # Fallback to text content
                metadata["publication_date"] = date_elem.text.strip()

    def _extract_identifiers(self, root: ET.Element, metadata: Dict[str, Any]) -> None:
        """Extract ISSN and other identifiers"""
        issn_elem = root.find('.//tei:idno[@type="ISSN"]', self.ns)
        if issn_elem is not None and issn_elem.text:
            metadata["issn"] = issn_elem.text.strip()

        eissn_elem = root.find('.//tei:idno[@type="eISSN"]', self.ns)
        if eissn_elem is not None and eissn_elem.text:
            metadata["eissn"] = eissn_elem.text.strip()

    def _extract_affiliations(
        self, root: ET.Element, metadata: Dict[str, Any]
    ) -> Dict[str, str]:
        """Extract institution names from affiliations - institution names only"""
        # path: affiliations are typically in teiHeader/fileDesc/sourceDesc
        affiliation_elems = root.findall(
            ".//tei:teiHeader//tei:affiliation[@key]", self.ns
        )
        if not affiliation_elems:
            # Fallback to document-wide search if not found in header
            affiliation_elems = root.findall(".//tei:affiliation[@key]", self.ns)
        affiliation_index = {}

        for aff_elem in affiliation_elems:
            aff_key = aff_elem.get("key")
            if aff_key and aff_key not in affiliation_index:
                # Prefer institution; otherwise safely fallback within the same affiliation
                chosen_elem = (
                    aff_elem.find('.//tei:orgName[@type="institution"]', self.ns)
                    or aff_elem.find('.//tei:orgName[@type="laboratory"]', self.ns)
                    or aff_elem.find('.//tei:orgName[@type="department"]', self.ns)
                    or aff_elem.find(".//tei:orgName", self.ns)
                )
                if chosen_elem is not None and chosen_elem.text:
                    chosen_name = chosen_elem.text.strip()
                    if chosen_name:
                        affiliation_index[aff_key] = chosen_name
                        metadata["affiliations"].append(chosen_name)

        return affiliation_index

    def _extract_authors(
        self, root: ET.Element, metadata: Dict[str, Any], affiliation_index: dict
    ) -> None:
        """Extract all authors and link to affiliations"""
        # path: authors are typically in teiHeader/fileDesc/sourceDesc
        author_elems = root.findall(".//tei:teiHeader//tei:author", self.ns)
        if not author_elems:
            # Fallback to document-wide search if not found in header
            author_elems = root.findall(".//tei:author", self.ns)

        for author_elem in author_elems:
            author = {
                "forename": None,
                "middle_name": None,
                "surname": None,
                "role": None,
                "email": None,
                "is_corresponding": False,
                "affiliations": [],
            }

            # Check if corresponding author
            if author_elem.get("role") == "corresp":
                author["is_corresponding"] = True

            # Extract name parts
            persname_elem = author_elem.find(".//tei:persName", self.ns)
            if persname_elem is not None:
                # Forename (typed) and middle (typed)
                forename_elem = persname_elem.find(
                    './/tei:forename[@type="first"]', self.ns
                )
                if forename_elem is not None and forename_elem.text:
                    author["forename"] = forename_elem.text.strip()

                middle_elem = persname_elem.find(
                    './/tei:forename[@type="middle"]', self.ns
                )
                if middle_elem is not None and middle_elem.text:
                    author["middle_name"] = middle_elem.text.strip()

                # Fallback for untyped forenames: use first as forename, second as middle
                untyped_forenames = []
                for fn in persname_elem.findall(".//tei:forename", self.ns):
                    if (
                        fn is not None
                        and fn.get("type") is None
                        and fn.text
                        and fn.text.strip()
                    ):
                        untyped_forenames.append(fn.text.strip())
                if not author["forename"] and untyped_forenames:
                    author["forename"] = untyped_forenames[0]
                if not author["middle_name"]:
                    if author["forename"] and untyped_forenames:
                        # If forename came from untyped index 0, prefer next untyped for middle
                        if (
                            untyped_forenames[0] == author["forename"]
                            and len(untyped_forenames) > 1
                        ):
                            author["middle_name"] = untyped_forenames[1]
                        elif untyped_forenames[0] != author["forename"]:
                            author["middle_name"] = untyped_forenames[0]

                # Surname
                surname_elem = persname_elem.find(".//tei:surname", self.ns)
                if surname_elem is not None and surname_elem.text:
                    author["surname"] = surname_elem.text.strip()

                # Role/title
                role_elem = persname_elem.find(".//tei:roleName", self.ns)
                if role_elem is not None and role_elem.text:
                    author["role"] = role_elem.text.strip()

            # Email
            email_elem = author_elem.find(".//tei:email", self.ns)
            if email_elem is not None and email_elem.text:
                author["email"] = email_elem.text.strip()

            # Extract affiliations: support both @key and @ref
            aff_keys: List[str] = []
            for aff_elem in author_elem.findall(".//tei:affiliation[@key]", self.ns):
                key = aff_elem.get("key")
                if key:
                    aff_keys.append(key)
            for aff_elem in author_elem.findall(".//tei:affiliation[@ref]", self.ns):
                ref = aff_elem.get("ref")
                if ref:
                    aff_keys.append(ref.lstrip("#"))

            # Link strictly by key when possible, with safe local fallback
            seen_affiliations = set()
            for key in aff_keys:
                if key in affiliation_index:
                    name = affiliation_index[key]
                    if name and name not in seen_affiliations:
                        author["affiliations"].append(name)
                        seen_affiliations.add(name)
                else:
                    # Local fallback: derive a best name from the author's own affiliation element
                    local_aff = author_elem.find(
                        f".//tei:affiliation[@key='{key}']", self.ns
                    ) or author_elem.find(f".//tei:affiliation[@ref='#{key}']", self.ns)
                    if local_aff is not None:
                        local_name_elem = (
                            local_aff.find(
                                './/tei:orgName[@type="institution"]', self.ns
                            )
                            or local_aff.find(
                                './/tei:orgName[@type="laboratory"]', self.ns
                            )
                            or local_aff.find(
                                './/tei:orgName[@type="department"]', self.ns
                            )
                            or local_aff.find(".//tei:orgName", self.ns)
                        )
                        if local_name_elem is not None and local_name_elem.text:
                            local_name = local_name_elem.text.strip()
                            if local_name and local_name not in seen_affiliations:
                                author["affiliations"].append(local_name)
                                seen_affiliations.add(local_name)

            # Only add author if we have at least a name
            if author["forename"] or author["surname"]:
                metadata["authors"].append(author)

    def extract_summary(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract a summary of key fields for display"""
        return {
            "title": metadata["title"],
            "doi": metadata["doi"],
            "journal": metadata["journal"],
            "publisher": metadata["publisher"],
            "publication_date": metadata["publication_date"],
            "author_count": len(metadata["authors"]),
            "authors": [
                {
                    "forename": author["forename"],
                    "middle_name": author["middle_name"],
                    "surname": author["surname"],
                    "lastname": author["surname"],
                    "role": author["role"],
                    "email": author["email"] if author["is_corresponding"] else None,
                    "affiliations": author["affiliations"],
                }
                for author in metadata["authors"]  # Include ALL authors
            ],
            "volume": metadata["volume"],
            "issue": metadata["issue"],
            "pages": metadata["pages"],
        }

    def parse_references_file(self, xml_path: str) -> List[Dict[str, Any]]:
        """Parse a GROBID references XML file and extract references"""
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            return self._extract_references(root)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML file: {e}")
        except Exception as e:
            raise ValueError(f"Error parsing references file {xml_path}: {e}")

    def parse_references_string(self, xml_content: str) -> List[Dict[str, Any]]:
        """Parse XML content string and extract references"""
        try:
            root = ET.fromstring(xml_content)
            return self._extract_references(root)
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML content: {e}")

    def _extract_references(self, root: ET.Element) -> List[Dict[str, Any]]:
        """Extract ALL references with title OR DOI from TEI XML"""
        references = []

        # path: references are typically in text/back/div/listBibl
        bibl_structs = root.findall(
            ".//tei:text//tei:listBibl//tei:biblStruct", self.ns
        )
        if not bibl_structs:
            # Fallback to document-wide search if not found in expected location
            bibl_structs = root.findall(".//tei:biblStruct", self.ns)

        for bibl in bibl_structs:
            reference: Dict[str, Optional[str]] = {
                "id": None,
                "title": None,
                "doi": None,
            }

            # Extract reference ID
            ref_id = bibl.get("{http://www.w3.org/XML/1998/namespace}id")
            if ref_id:
                reference["id"] = ref_id

            # Strategy 1: Try journal article (analytic section)
            title, doi = self._extract_from_analytic(bibl)

            # Strategy 2: Try book/monograph (monogr section) if analytic failed
            if not title and not doi:
                title, doi = self._extract_from_monogr(bibl)

            # Strategy 3: Fallback - search anywhere in biblStruct
            if not title and not doi:
                title, doi = self._extract_fallback(bibl)

            reference["title"] = title
            reference["doi"] = doi

            # Include if we have EITHER title OR DOI
            if reference["title"] or reference["doi"]:
                references.append(reference)

        return references

    def _extract_from_analytic(self, bibl):
        """Extract title and DOI from analytic section (journal articles)"""
        analytic = bibl.find(".//tei:analytic", self.ns)
        if analytic is None:
            return None, None

        # Title: article level
        title = self._safe_extract_text(
            analytic.find('.//tei:title[@level="a"][@type="main"]', self.ns)
        )

        # DOI from analytic
        doi = self._safe_extract_text(
            analytic.find('.//tei:idno[@type="DOI"]', self.ns)
        )

        return title, doi

    def _extract_from_monogr(self, bibl):
        """Extract title and DOI from monogr section (books/reports)"""
        monogr = bibl.find(".//tei:monogr", self.ns)
        if monogr is None:
            return None, None

        # Title: book/monograph level
        title = self._safe_extract_text(
            monogr.find('.//tei:title[@level="m"][@type="main"]', self.ns)
        )

        # DOI from monogr
        doi = self._safe_extract_text(monogr.find('.//tei:idno[@type="DOI"]', self.ns))

        return title, doi

    def _extract_fallback(self, bibl):
        """Fallback extraction - search anywhere in biblStruct"""
        # Try any title anywhere
        title = self._safe_extract_text(bibl.find(".//tei:title", self.ns))

        # Try any DOI anywhere
        doi = self._safe_extract_text(bibl.find('.//tei:idno[@type="DOI"]', self.ns))

        return title, doi

    def _safe_extract_text(self, element):
        """Safely extract and clean text from XML element"""
        if element is not None and element.text and element.text.strip():
            text = element.text.strip()
            # Clean DOI if this looks like one
            if element.get("type") == "DOI":
                text = re.sub(r"\?.*$", "", text)
            return text
        return None


# Convenience functions


def parse_grobid_xml(xml_path: str) -> Dict[str, Any]:
    """Convenience function to parse a GROBID XML file"""
    parser = GrobidTEIParser()
    return parser.parse_file(xml_path)


def parse_grobid_xml_string(xml_content: str) -> Dict[str, Any]:
    """Convenience function to parse GROBID XML content"""
    parser = GrobidTEIParser()
    return parser.parse_string(xml_content)


def parse_grobid_references(xml_path: str) -> List[Dict[str, Any]]:
    """Convenience function to parse a GROBID references XML file"""
    parser = GrobidTEIParser()
    return parser.parse_references_file(xml_path)


def parse_grobid_references_string(xml_content: str) -> List[Dict[str, Any]]:
    """Convenience function to parse GROBID references XML content"""
    parser = GrobidTEIParser()
    return parser.parse_references_string(xml_content)

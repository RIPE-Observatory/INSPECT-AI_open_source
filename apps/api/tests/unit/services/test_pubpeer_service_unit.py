import json

import pytest
from bs4 import BeautifulSoup

from core.services.pubpeer_service import PubPeerService


def _pubpeer_component_html() -> str:
    comments = [
        {
            "id": 219696,
            "inner_id": 1,
            "markdown": "Fig 7 A.\n\n![file](https://pubpeer.com/storage/example.png)\n\nComment body.",
            "html": '<p>Fig 7 A.</p><p><a href="https://pubpeer.com/storage/example.png">file</a></p><p>Comment body.</p>',
            "user_alias": "Hoya Camphorifolia",
            "is_from_author": False,
            "accepted_at": "2021-08-25T02:57:23.000000Z",
            "user": {"display_name": "Hoya Camphorifolia"},
        },
        {
            "id": 224939,
            "inner_id": 2,
            "markdown": "Retracted [12 October 2021](https://example.org/retraction).",
            "html": '<p>Retracted <a href="https://example.org/retraction">12 October 2021</a>.</p>',
            "user_alias": None,
            "is_from_author": True,
            "accepted_at": "2021-10-15T19:00:38.000000Z",
            "user": {"display_name": "Author Name"},
        },
    ]
    publication = {
        "updates": [
            {
                "action": "RETRACTED",
                "content": json.dumps(
                    {
                        "timestamp": 1638325144,
                        "identifier": {"pubmed": "34647793"},
                        "type": "Retracted",
                    }
                ),
            }
        ]
    }
    return f"""
    <publication-page :data-publication='{json.dumps(publication)}'></publication-page>
    <comment-timeline :data-comments='{json.dumps(comments)}'></comment-timeline>
    """


@pytest.mark.unit
class TestPubPeerServiceUnit:
    def test_extracts_comments_from_pubpeer_component_json(self):
        service = PubPeerService()
        soup = BeautifulSoup(_pubpeer_component_html(), "html.parser")

        comments = service._comments_from_component(soup)

        assert len(comments) == 2
        assert comments[0].id == 1
        assert comments[0].author == "Hoya Camphorifolia"
        assert comments[0].date == "2021-08-25T02:57:23.000000Z"
        assert "Comment body" in comments[0].comment
        assert comments[0].links == ["https://pubpeer.com/storage/example.png"]
        assert comments[1].is_author_response is True
        assert comments[1].author == "Author Name"

    def test_extracts_publication_status_from_pubpeer_component_json(self):
        service = PubPeerService()
        soup = BeautifulSoup(_pubpeer_component_html(), "html.parser")

        statuses = service._extract_publication_status_from_component(soup)

        assert len(statuses) == 1
        assert statuses[0].status == "RETRACTED"
        assert statuses[0].link == "https://pubmed.ncbi.nlm.nih.gov/34647793/"

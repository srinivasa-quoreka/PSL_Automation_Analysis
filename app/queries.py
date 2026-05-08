"""
Predefined Jira queries for different dashboards.

Add new queries here as dictionaries with a name and JQL.
You can also override the default query via .env JIRA_JQL.
"""

QUERIES = {
    "default": {
        "name": "Default Test Cases",
        "jql": 'issuetype = "Test"',
        "description": "All test cases",
    },
    "web": {
        "name": "Web Platform Tests",
        "jql": 'project = "WEB" AND issuetype = "Test"',
        "description": "Test cases for web platform",
    },
    "mobile": {
        "name": "Mobile Platform Tests",
        "jql": 'project = "MOB" AND issuetype = "Test"',
        "description": "Test cases for mobile platform",
    },
    "api": {
        "name": "API Tests",
        "jql": 'project = "API" AND issuetype = "Test"',
        "description": "Test cases for API endpoints",
    },
    "regression": {
        "name": "Regression Test Suite",
        "jql": 'issuetype = "Test" AND labels = "regression"',
        "description": "Regression test cases",
    },
    "smoke": {
        "name": "Smoke Test Suite",
        "jql": 'issuetype = "Test" AND labels = "smoke"',
        "description": "Smoke test cases",
    },
}


def get_query(dashboard_name: str | None = None) -> dict:
    """
    Get query definition by dashboard name.
    
    Args:
        dashboard_name: Name of the dashboard (key in QUERIES). 
                       If None or not found, returns default.
    
    Returns:
        dict with 'name', 'jql', 'description'
    """
    if dashboard_name and dashboard_name in QUERIES:
        return QUERIES[dashboard_name]
    return QUERIES["default"]


def list_dashboards() -> list:
    """Return list of available dashboards with metadata."""
    return [
        {
            "id": key,
            "name": config["name"],
            "description": config["description"],
        }
        for key, config in QUERIES.items()
    ]

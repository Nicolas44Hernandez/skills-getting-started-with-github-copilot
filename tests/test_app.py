"""
Tests for the High School Management System API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI application"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {}
    for name, details in activities.items():
        original_activities[name] = {
            "description": details["description"],
            "schedule": details["schedule"],
            "max_participants": details["max_participants"],
            "participants": details["participants"].copy()
        }
    
    yield
    
    # Restore original state after test
    for name in activities:
        activities[name]["participants"] = original_activities[name]["participants"].copy()


class TestRoot:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root path redirects to static index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for the GET /activities endpoint"""
    
    def test_get_activities_success(self, client):
        """Test successful retrieval of all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert "Gym Class" in data
        
    def test_get_activities_structure(self, client):
        """Test that activities have correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        # Check structure of first activity
        chess_club = data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)


class TestSignupForActivity:
    """Tests for the POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_success(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Chess Club/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        assert "Chess Club" in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "newstudent@mergington.edu" in activities_data["Chess Club"]["participants"]
    
    def test_signup_activity_not_found(self, client):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Club/signup",
            params={"email": "student@mergington.edu"}
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_signup_duplicate_participant(self, client):
        """Test that duplicate signup is rejected"""
        email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"]
    
    def test_signup_special_characters_in_activity_name(self, client):
        """Test signup with URL-encoded activity name"""
        response = client.post(
            "/activities/Programming Class/signup",
            params={"email": "coder@mergington.edu"}
        )
        assert response.status_code == 200


class TestRemoveParticipant:
    """Tests for the DELETE /activities/{activity_name}/participants/{email} endpoint"""
    
    def test_remove_participant_success(self, client):
        """Test successful removal of a participant"""
        # First, add a participant
        email = "removeme@mergington.edu"
        client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        
        # Then remove them
        response = client.delete(
            f"/activities/Chess Club/participants/{email}"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "Removed" in data["message"]
        assert email in data["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data["Chess Club"]["participants"]
    
    def test_remove_existing_participant(self, client):
        """Test removal of an existing participant from initial data"""
        # michael@mergington.edu is already in Chess Club
        email = "michael@mergington.edu"
        
        response = client.delete(
            f"/activities/Chess Club/participants/{email}"
        )
        assert response.status_code == 200
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data["Chess Club"]["participants"]
    
    def test_remove_participant_activity_not_found(self, client):
        """Test removal from non-existent activity"""
        response = client.delete(
            "/activities/Nonexistent Club/participants/student@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_remove_participant_not_in_activity(self, client):
        """Test removal of participant not in the activity"""
        response = client.delete(
            "/activities/Chess Club/participants/notregistered@mergington.edu"
        )
        assert response.status_code == 404
        assert "Participant not found" in response.json()["detail"]
    
    def test_remove_participant_special_characters_in_email(self, client):
        """Test removal with special characters in email"""
        # Add participant with special chars
        email = "test+special@mergington.edu"
        client.post(
            "/activities/Chess Club/signup",
            params={"email": email}
        )
        
        # Remove them
        response = client.delete(
            f"/activities/Chess Club/participants/{email}"
        )
        assert response.status_code == 200


class TestIntegration:
    """Integration tests for complete workflows"""
    
    def test_full_signup_and_removal_workflow(self, client):
        """Test complete workflow of signup and removal"""
        email = "workflow@mergington.edu"
        activity = "Programming Class"
        
        # Check initial state
        initial_response = client.get("/activities")
        initial_data = initial_response.json()
        initial_count = len(initial_data[activity]["participants"])
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity}/signup",
            params={"email": email}
        )
        assert signup_response.status_code == 200
        
        # Verify signup
        after_signup = client.get("/activities")
        after_signup_data = after_signup.json()
        assert email in after_signup_data[activity]["participants"]
        assert len(after_signup_data[activity]["participants"]) == initial_count + 1
        
        # Remove participant
        remove_response = client.delete(
            f"/activities/{activity}/participants/{email}"
        )
        assert remove_response.status_code == 200
        
        # Verify removal
        after_removal = client.get("/activities")
        after_removal_data = after_removal.json()
        assert email not in after_removal_data[activity]["participants"]
        assert len(after_removal_data[activity]["participants"]) == initial_count
    
    def test_multiple_activities_signup(self, client):
        """Test signing up for multiple activities"""
        email = "multitasker@mergington.edu"
        
        # Sign up for multiple activities
        activities_to_join = ["Chess Club", "Programming Class", "Art Studio"]
        
        for activity in activities_to_join:
            response = client.post(
                f"/activities/{activity}/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify all signups
        response = client.get("/activities")
        data = response.json()
        
        for activity in activities_to_join:
            assert email in data[activity]["participants"]

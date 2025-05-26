import pytest
from sqlalchemy.exc import IntegrityError


# Test User Model CRUD and Constraints
def test_create_user(db_session, models_fixture):
    new_user = models_fixture.User(
        username="testuser", email="test@example.com", api_key="testapikey"
    )
    db_session.add(new_user)
    db_session.commit()
    db_session.refresh(new_user)

    assert new_user.id is not None
    assert new_user.username == "testuser"
    assert new_user.email == "test@example.com"


def test_read_user(db_session, models_fixture):
    user = (
        db_session.query(models_fixture.User)
        .filter_by(username="testuser")
        .first()
    )
    assert user is not None
    assert user.email == "test@example.com"


def test_update_user(db_session, models_fixture):
    user = (
        db_session.query(models_fixture.User)
        .filter_by(username="testuser")
        .first()
    )
    assert user is not None
    user.email = "updated@example.com"
    db_session.commit()
    db_session.refresh(user)
    assert user.email == "updated@example.com"


def test_delete_user(db_session, models_fixture):
    user = (
        db_session.query(models_fixture.User)
        .filter_by(username="testuser")
        .first()
    )
    assert user is not None
    db_session.delete(user)
    db_session.commit()
    deleted_user = (
        db_session.query(models_fixture.User)
        .filter_by(username="testuser")
        .first()
    )
    assert deleted_user is None


def test_user_username_unique_constraint(db_session, models_fixture):
    user1 = models_fixture.User(
        username="uniqueuser", email="unique1@example.com", api_key="key1"
    )
    db_session.add(user1)
    db_session.commit()

    user2 = models_fixture.User(
        username="uniqueuser", email="unique2@example.com", api_key="key2"
    )
    db_session.add(user2)
    with pytest.raises(IntegrityError):
        db_session.commit()  # Should fail due to unique username constraint
    db_session.rollback()  # Rollback the failed transaction


def test_user_email_null_constraint(db_session, models_fixture):
    with pytest.raises(IntegrityError):
        user_no_email = models_fixture.User(
            username="noemailuser", api_key="keynoemail"
        )  # email is nullable=False
        db_session.add(user_no_email)
        db_session.commit()
    db_session.rollback()


# --- APISpecification Model Tests (Example) ---
def test_create_api_specification(db_session, models_fixture):
    # First, create a user to associate with the API spec
    owner_user = models_fixture.User(
        username="specowner", email="specowner@example.com", api_key="speckey"
    )
    db_session.add(owner_user)
    db_session.commit()
    db_session.refresh(owner_user)

    api_spec = models_fixture.APISpecification(
        name="Test API",
        version_string="v1.0",
        openapi_content={
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "v1.0"},
        },
        user_id=owner_user.id,
    )
    db_session.add(api_spec)
    db_session.commit()
    db_session.refresh(api_spec)

    assert api_spec.id is not None
    assert api_spec.name == "Test API"
    assert api_spec.owner == owner_user


def test_api_specification_foreign_key_constraint(db_session, models_fixture):
    # Attempt to create an API spec with a non-existent user_id
    with pytest.raises(IntegrityError):
        api_spec_bad_fk = models_fixture.APISpecification(
            name="Bad FK API",
            version_string="v1.0",
            openapi_content={"openapi": "3.0.0"},
            user_id=99999,  # Assuming this user ID does not exist
        )
        db_session.add(api_spec_bad_fk)
        db_session.commit()
    db_session.rollback()


# TODO: Add similar CRUD and constraint tests for:
# - HARUpload
# - MockConfiguration
# - ValidationRun # - MockConfiguration
# - ValidationRun

from app.features.login.urls import LOGIN, LOGIN_POST, LOGOUT
from app.features.signup.urls import SIGNUP_POST
from tests.conftest import login

# The prefix that session.require protects in app/main.py.
PROTECTED = "/app"


async def test_a_protected_page_sends_a_visitor_to_login(client):
    r = await client.get(PROTECTED, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers.get("location") == LOGIN.href()
    r = await client.get(PROTECTED, headers={"datastar-request": "true"})
    assert "window.location" in r.text


async def test_a_wrong_password_sets_the_error_signal(client):
    r = await client.post(LOGIN_POST.href(), json={"email": "ada@example.com", "password": "no"})
    assert "Wrong email or password" in r.text
    assert "window.location" not in r.text


async def test_login_then_logout(client):
    await login(client)
    assert (await client.get(PROTECTED, follow_redirects=False)).status_code != 303
    await client.post(LOGOUT.href())
    assert (await client.get(PROTECTED, follow_redirects=False)).status_code == 303


async def test_signup_signs_in_and_rejects_a_taken_email(client):
    body = {"email": "bob@example.com", "password": "long-enough-pw"}
    assert "window.location" in (await client.post(SIGNUP_POST.href(), json=body)).text
    assert (await client.get(PROTECTED, follow_redirects=False)).status_code != 303
    r = await client.post(SIGNUP_POST.href(), json=body)
    assert "already registered" in r.text

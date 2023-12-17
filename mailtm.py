import requests
import time
import json
import asyncio
import aio_msgpack_rpc


MAILTM_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}


class MailTmError(Exception):
    pass


def _make_mailtm_request(request_fn, timeout=600):
    tstart = time.monotonic()
    error = None
    status_code = None
    while time.monotonic() - tstart < timeout:
        try:
            r = request_fn()
            status_code = r.status_code
            if status_code == 200 or status_code == 201:
                return r.json()
            if status_code != 429:
                break
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            error = e
        time.sleep(1.0)

    if error is not None:
        raise MailTmError(error) from error
    if status_code is not None:
        raise MailTmError(f"Status code: {status_code}")
    if time.monotonic() - tstart >= timeout:
        raise MailTmError("timeout")
    raise MailTmError("unknown error")


def get_mailtm_domains():
    def _domain_req():
        return requests.get("https://api.mail.tm/domains", headers=MAILTM_HEADERS)

    r = _make_mailtm_request(_domain_req)

    return [x['domain'] for x in r]


def create_mailtm_account(address, password):
    account = json.dumps({"address": address, "password": password})

    def _acc_req():
        return requests.post(
            "https://api.mail.tm/accounts", data=account, headers=MAILTM_HEADERS)

    r = _make_mailtm_request(_acc_req)
    assert len(r['id']) > 0
    return r


def get_mailtm_token(account_id, password):
    data = json.dumps({"account": account_id, "password": password})

    def _token_req():
        return requests.post("https://api.mail.tm/token", data=data, headers=MAILTM_HEADERS)
    r = _make_mailtm_request(_token_req)
    return r['token']

# List Email Headers with pagination


def list_email_headers(token, page=1):
    def _headers_req():
        return requests.get(f"https://api.mail.tm/messages?page={page}", headers={"Authorization": f"Bearer {token}"})
    r = _make_mailtm_request(_headers_req)
    return r['hydra:member'], r['hydra:view']

# Notify server of email:


async def notify_server(mail_title, mail_body):
    async with aio_msgpack_rpc.Session("localhost", 18000) as session:
        await session.call('on_new_mail', mail_title, mail_body)

# Read Mail


def read_email(token, message_id):
    def _email_req():
        return requests.get(f"https://api.mail.tm/messages{message_id}", headers={"Authorization": f"Bearer {token}"})
    r = _make_mailtm_request(_email_req)
    return r['subject'], r['test']

# Main Loop


async def main_loop():
    # create account
    domain = get_mailtm_domains()[0]
    account_id = f"test_15user@{domain}"
    password = "Password123"
    print(domain)
    create_mailtm_account(account_id, password)
    token = get_mailtm_token(account_id, password)

    seen_emails = set()
    while True:
        headers, view = list_email_headers(token)
        for header in headers:
            if header['id'] not in seen_emails:
                seen_emails.add(header['id'])
                subject, body = read_email(token, header['id'])
                await notify_server(subject, body)

        # Sleep for 10secs and check again
        await asyncio.sleep(10)

# Main loop Run
try:
    asyncio.run(main_loop())
except KeyboardInterrupt:
    pass

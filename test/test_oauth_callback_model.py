import unittest

from models import SessionOAuthCallbackBody


class SessionOAuthCallbackBodyTests(unittest.TestCase):
    def test_accepts_null_web3_account_for_google_callback(self):
        body = SessionOAuthCallbackBody.model_validate({
            "login_type": "google",
            "code": "CODE",
            "state": "STATE",
            "redirect_url": "https://auth.neofantasy.online/callback/google",
            "web3_account": None,
        })

        self.assertIsNone(body.web3_account)


if __name__ == "__main__":
    unittest.main()

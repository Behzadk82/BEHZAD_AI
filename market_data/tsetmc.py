
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone


class TSETMCClient:
    """
    Client for testing access to public TSETMC market data.
    This module does not place trades or send orders.
    """

    BASE_URL = "https://www.tsetmc.com"

    def __init__(self, timeout=15):
        self.timeout = timeout

    def check_connection(self):
        url = self.BASE_URL + "/"

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 BEHZAD_AI/0.4",
                "Accept": "text/html,application/json"
            }
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout
            ) as response:

                status = response.status

                return {
                    "success": 200 <= status < 300,
                    "source": "TSETMC",
                    "http_status": status,
                    "checked_at": datetime.now(
                        timezone.utc
                    ).isoformat(),
                    "message": "Connection successful"
                }

        except urllib.error.HTTPError as error:
            return {
                "success": False,
                "source": "TSETMC",
                "http_status": error.code,
                "message": "HTTP error"
            }

        except Exception as error:
            return {
                "success": False,
                "source": "TSETMC",
                "http_status": None,
                "message": "Connection failed",
                "error_type": type(error).__name__
            }


if __name__ == "__main__":
    client = TSETMCClient()
    print(json.dumps(
        client.check_connection(),
        ensure_ascii=False,
        indent=2
    ))
  

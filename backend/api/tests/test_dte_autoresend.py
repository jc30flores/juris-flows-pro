from unittest.mock import patch

from django.test import SimpleTestCase

from api.dte_cf_service import check_hacienda_online


class DteAutoresendHealthcheckTests(SimpleTestCase):
    @patch("api.dte_cf_service.requests.get")
    def test_check_hacienda_online_returns_true_on_200(self, mock_get):
        mock_get.return_value.status_code = 200
        self.assertTrue(check_hacienda_online())

    @patch("api.dte_cf_service.requests.get")
    def test_check_hacienda_online_returns_false_on_non_200(self, mock_get):
        mock_get.return_value.status_code = 503
        self.assertFalse(check_hacienda_online())

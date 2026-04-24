from unittest.mock import Mock

from argus_cli.services.lookup import GeoIPLookup


class TestLookupIP:
    def test_successful_lookup(self):
        city_reader = Mock()
        city_response = Mock()
        city_response.city.name = "Mountain View"
        city_response.subdivisions.most_specific.name = "California"
        city_response.country.name = "United States"
        city_response.country.iso_code = "US"
        city_response.postal.code = "94035"
        city_reader.city.return_value = city_response

        asn_reader = Mock()
        asn_response = Mock()
        asn_response.autonomous_system_number = 15169
        asn_response.autonomous_system_organization = "GOOGLE"
        asn_reader.asn.return_value = asn_response

        proxy_db = Mock()
        proxy_db.get_all.return_value = {
            "proxy_type": "DCH",
            "country_short": "US",
            "isp": "Google LLC",
            "domain": "google.com",
            "usage_type": "DCH",
        }

        lookup_service = GeoIPLookup("", "", "", "")
        lookup_service.has_proxy_db = True
        result = lookup_service.lookup_ip(city_reader, asn_reader, proxy_db, None, None, "8.8.8.8")

        assert result["ip"] == "8.8.8.8"
        assert result["city"] == "Mountain View"
        assert result["country"] == "United States"
        assert result["iso_code"] == "US"
        assert result["asn"] == 15169
        assert result["asn_org"] == "GOOGLE"
        assert result["proxy_type"] == "DCH"
        assert result["usage_type"] == "DCH"
        assert result["org_managed"] is False
        assert result["org_id"] is None
        assert result["platform"] is None
        assert result["error"] is None

    def test_ip_not_found(self):
        city_reader = Mock()
        asn_reader = Mock()

        import geoip2.errors

        city_reader.city.side_effect = geoip2.errors.AddressNotFoundError("IP not found")

        lookup_service = GeoIPLookup("", "", "", "")
        result = lookup_service.lookup_ip(city_reader, asn_reader, None, None, None, "1.2.3.4")

        assert result["ip"] == "1.2.3.4"
        assert result["error"] == "IP not found in database"

    def test_invalid_ip_format(self):
        city_reader = Mock()
        asn_reader = Mock()
        city_reader.city.side_effect = ValueError("Invalid IP")

        lookup_service = GeoIPLookup("", "", "", "")
        result = lookup_service.lookup_ip(city_reader, asn_reader, None, None, None, "invalid")

        assert result["ip"] == "invalid"
        assert result["error"] == "Invalid IP format"

    def test_ipinfo_domain_enrichment(self):
        city_reader = Mock()
        city_response = Mock()
        city_response.city.name = "Mountain View"
        city_response.subdivisions.most_specific.name = "California"
        city_response.country.name = "United States"
        city_response.country.iso_code = "US"
        city_response.postal.code = "94035"
        city_reader.city.return_value = city_response

        asn_reader = Mock()
        asn_response = Mock()
        asn_response.autonomous_system_number = 15169
        asn_response.autonomous_system_organization = "GOOGLE"
        asn_reader.asn.return_value = asn_response

        ipinfo_reader = Mock()
        ipinfo_reader.get.return_value = {"as_domain": "google.com", "asn": "AS15169"}

        lookup_service = GeoIPLookup("", "", "", "")
        lookup_service.has_ipinfo_db = True
        result = lookup_service.lookup_ip(city_reader, asn_reader, None, ipinfo_reader, None, "8.8.8.8")

        assert result["domain"] == "google.com"

    def test_ipinfo_failure_does_not_break_lookup(self):
        city_reader = Mock()
        city_response = Mock()
        city_response.city.name = "Mountain View"
        city_response.subdivisions.most_specific.name = "California"
        city_response.country.name = "United States"
        city_response.country.iso_code = "US"
        city_response.postal.code = "94035"
        city_reader.city.return_value = city_response

        asn_reader = Mock()
        asn_response = Mock()
        asn_response.autonomous_system_number = 15169
        asn_response.autonomous_system_organization = "GOOGLE"
        asn_reader.asn.return_value = asn_response

        ipinfo_reader = Mock()
        ipinfo_reader.get.side_effect = Exception("DB read error")

        lookup_service = GeoIPLookup("", "", "", "")
        lookup_service.has_ipinfo_db = True
        result = lookup_service.lookup_ip(city_reader, asn_reader, None, ipinfo_reader, None, "8.8.8.8")

        assert result["domain"] is None
        assert result["error"] is None
        assert result["ip"] == "8.8.8.8"

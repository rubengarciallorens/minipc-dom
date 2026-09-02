import unittest
from decimal import Decimal

import bot


SAMPLE_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Mini PC Beelink Intel N100 16GB RAM 512GB SSD por 89,99 EUR</title>
      <link>https://www.chollometro.com/ofertas/mini-pc-valido</link>
      <guid>valid-1</guid>
      <description>Incluye Ethernet Gigabit y Wi-Fi.</description>
    </item>
    <item>
      <title>Mini PC Intel N100 8GB RAM 256GB SSD por 100 EUR</title>
      <link>https://www.chollometro.com/ofertas/precio-limite</link>
      <guid>limit-1</guid>
      <description>Equipo completo.</description>
    </item>
    <item>
      <title>Barebone Mini PC Intel N100 por 79 EUR sin RAM ni SSD</title>
      <link>https://www.chollometro.com/ofertas/barebone</link>
      <guid>barebone-1</guid>
      <description>Solo barebone.</description>
    </item>
    <item>
      <title>Soporte para mini PC por 12,50 EUR</title>
      <link>https://www.chollometro.com/ofertas/soporte</link>
      <guid>accessory-1</guid>
      <description>Accesorio VESA.</description>
    </item>
    <item>
      <title>Monitor LG UltraGear 27GX704A-B OLED por 549 EUR</title>
      <link>https://www.chollometro.com/ofertas/lg-27gx704</link>
      <guid>monitor-1</guid>
      <description>Monitor gaming QHD de 240 Hz.</description>
    </item>
  </channel>
</rss>
"""


class BotTests(unittest.TestCase):
    def test_parse_and_filter(self):
        entries = bot.parse_feed(SAMPLE_RSS)
        matches = bot.matching_deals(entries)
        self.assertEqual(len(entries), 5)
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0]["price"], Decimal("89.99"))
        self.assertEqual(matches[1]["alert_type"], "monitor")
        self.assertEqual(matches[1]["price"], Decimal("549"))

    def test_strictly_below_100(self):
        entry = {
            "title": "Mini PC Intel N100 8GB RAM 256GB SSD 100 €",
            "description": "Equipo completo con Ethernet Gigabit",
        }
        self.assertTrue(bot.is_suitable_minipc(entry))
        self.assertEqual(bot.extract_price(entry), Decimal("100"))
        self.assertFalse(bot.extract_price(entry) < bot.MAX_PRICE)

    def test_specs(self):
        entry = {
            "title": "Mini PC Intel N100 16GB RAM 512GB SSD",
            "description": "Ethernet",
        }
        specs = bot.detected_specs(entry)
        self.assertIn("N100", specs)
        self.assertIn("16 GB RAM", specs)
        self.assertIn("512 GB SSD", specs)

    def test_known_brand_without_literal_mini_pc(self):
        entry = {
            "title": "Beelink EQ12 Intel N100 16GB RAM 500GB SSD 95 €",
            "description": "Ordenador compacto con Ethernet",
        }
        self.assertTrue(bot.is_suitable_minipc(entry))

    def test_rejects_less_than_8gb_ram(self):
        entry = {
            "title": "Mini PC Intel N100 4GB RAM 256GB SSD 69 €",
            "description": "Ethernet Gigabit",
        }
        self.assertFalse(bot.is_suitable_minipc(entry))

    def test_rejects_emmc_or_missing_ssd(self):
        entry = {
            "title": "Mini PC Intel N100 8GB RAM 128GB eMMC 79 €",
            "description": "Ethernet Gigabit",
        }
        self.assertFalse(bot.is_suitable_minipc(entry))

    def test_rejects_small_ssd(self):
        entry = {
            "title": "Mini PC Intel N100 8GB RAM 64GB SSD 59 €",
            "description": "Ethernet Gigabit",
        }
        self.assertFalse(bot.is_suitable_minipc(entry))

    def test_rejects_missing_ethernet(self):
        entry = {
            "title": "Mini PC Intel N100 8GB RAM 256GB SSD 89 €",
            "description": "Wi-Fi 6 y Bluetooth",
        }
        self.assertFalse(bot.is_suitable_minipc(entry))

    def test_accepts_compact_specs(self):
        entry = {
            "title": "GMKtec G3 N100 8GB+256GB SSD 94,99 €",
            "description": "LAN Gigabit y Wi-Fi 6",
        }
        self.assertTrue(bot.is_suitable_minipc(entry))

    def test_accepts_monitor_model_variants(self):
        for model in ("27GX704", "27GX704A", "27GX704A-B", "27GX704AX-B"):
            with self.subTest(model=model):
                entry = {
                    "title": f"Monitor OLED LG {model}",
                    "description": "Oferta temporal",
                }
                self.assertTrue(bot.is_target_monitor(entry))

    def test_rejects_other_lg_monitor(self):
        entry = {
            "title": "Monitor OLED LG 27GX705A-B",
            "description": "Oferta temporal",
        }
        self.assertFalse(bot.is_target_monitor(entry))


if __name__ == "__main__":
    unittest.main()

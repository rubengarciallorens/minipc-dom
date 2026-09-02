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
  </channel>
</rss>
"""


class BotTests(unittest.TestCase):
    def test_parse_and_filter(self):
        entries = bot.parse_feed(SAMPLE_RSS)
        matches = bot.matching_deals(entries)
        self.assertEqual(len(entries), 4)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["price"], Decimal("89.99"))

    def test_strictly_below_100(self):
        entry = {
            "title": "Mini PC Intel N100 8GB RAM 256GB SSD 100 €",
            "description": "Equipo completo",
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
        self.assertIn("16GB RAM", specs)
        self.assertIn("512GB SSD", specs)

    def test_known_brand_without_literal_mini_pc(self):
        entry = {
            "title": "Beelink EQ12 Intel N100 16GB RAM 500GB SSD 95 €",
            "description": "Ordenador compacto con Ethernet",
        }
        self.assertTrue(bot.is_suitable_minipc(entry))


if __name__ == "__main__":
    unittest.main()

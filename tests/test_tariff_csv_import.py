"""
Tests para la importacion CSV del tarifario.
"""
import unittest

from fastapi import HTTPException

from backend.main import parse_tariff_csv_content


class TestTariffCsvImport(unittest.TestCase):
    def test_parse_valid_csv(self):
        csv_text = "\n".join([
            "code,description,category,max_price,tolerance_pct,expected_qty_min,expected_qty_max,applicable_claim_types",
            "rep-100,Parabrisas delantero,repuesto,250.50,10,1,2,choque_frontal;choque_lateral",
        ])

        result = parse_tariff_csv_content(csv_text)

        self.assertEqual(len(result["inserted"]), 1)
        self.assertEqual(result["inserted"][0]["code"], "REP-100")
        self.assertEqual(result["inserted"][0]["max_price"], 250.50)
        self.assertEqual(result["inserted"][0]["applicable_claim_types"], ["choque_frontal", "choque_lateral"])
        self.assertEqual(result["errors"], [])

    def test_missing_required_columns_raises_422(self):
        csv_text = "\n".join([
            "code,description,category",
            "REP-100,Parabrisas delantero,repuesto",
        ])

        with self.assertRaises(HTTPException) as ctx:
            parse_tariff_csv_content(csv_text)

        self.assertEqual(ctx.exception.status_code, 422)
        self.assertIn("max_price", ctx.exception.detail)

    def test_invalid_rows_are_reported_without_stopping_import(self):
        csv_text = "\n".join([
            "code,description,category,max_price,tolerance_pct,expected_qty_min,expected_qty_max",
            "REP-100,Parabrisas delantero,repuesto,250,10,1,2",
            "REP-101,Pieza invalida,repuesto,no-num,10,1,2",
            "REP-102,Categoria invalida,otra,50,10,1,2",
        ])

        result = parse_tariff_csv_content(csv_text)

        self.assertEqual(len(result["inserted"]), 1)
        self.assertEqual(len(result["errors"]), 2)
        self.assertEqual(result["errors"][0]["code"], "REP-101")

    def test_existing_and_duplicate_codes_are_skipped(self):
        csv_text = "\n".join([
            "code,description,category,max_price",
            "REP-100,Ya existe,repuesto,100",
            "REP-101,Nuevo,repuesto,120",
            "REP-101,Duplicado en archivo,repuesto,130",
        ])

        result = parse_tariff_csv_content(csv_text, existing_codes={"REP-100"})

        self.assertEqual([i["code"] for i in result["inserted"]], ["REP-101"])
        self.assertEqual([s["code"] for s in result["skipped"]], ["REP-100", "REP-101"])


if __name__ == "__main__":
    unittest.main()

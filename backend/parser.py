"""
Parser de facturas — convierte datos raw (JSON/XML) a estructura normalizada.
"""
import json
from typing import Dict, Any, List, Optional


def parse_invoice_json(raw_json: str) -> Optional[Dict[str, Any]]:
    """
    Parsear una factura desde formato JSON.
    Retorna dict normalizado con los campos requeridos.
    """
    try:
        data = json.loads(raw_json)
        return normalize_invoice(data)
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        return None


def normalize_invoice(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalizar la estructura de una factura a formato estándar.
    """
    items = []
    for item in data.get("items", []):
        items.append({
            "code": str(item.get("code", "")).strip().upper(),
            "description": str(item.get("description", "")).strip(),
            "category": str(item.get("category", "general")).strip().lower(),
            "quantity": float(item.get("quantity", 1)),
            "unit_price": float(item.get("unit_price", 0)),
            "total_price": float(item.get("total_price",
                                          item.get("quantity", 1) * item.get("unit_price", 0))),
        })

    subtotal = sum(i["total_price"] for i in items)
    iva = subtotal * 0.15  # IVA Ecuador 15%
    total = subtotal + iva

    return {
        "invoice_number": data.get("invoice_number", ""),
        "ruc": data.get("ruc", ""),
        "issue_date": data.get("issue_date", ""),
        "items": items,
        "subtotal": round(subtotal, 2),
        "iva": round(iva, 2),
        "total": round(total, 2),
    }


def validate_ruc(ruc: str) -> bool:
    """Validación básica de RUC ecuatoriano (13 dígitos)."""
    if not ruc or len(ruc) != 13:
        return False
    return ruc.isdigit()

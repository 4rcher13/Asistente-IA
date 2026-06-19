"""
CybersecurityMCP — Conector a bases de datos de seguridad para Ícaro.

Integra fuentes como MITRE CVE/ATT&CK y OWASP para responder preguntas
sobre vulnerabilidades, técnicas de ataque y mejores prácticas de seguridad.
"""
import logging
from typing import Optional, Dict

from ..core.shared_memory import log_event

logger = logging.getLogger(__name__)

try:
    import requests
    _REQUESTS_AVAILABLE = True
except ImportError:
    _REQUESTS_AVAILABLE = False


# Mapa de mejores prácticas OWASP Top 10 (local, carga instantánea)
_OWASP_TOP10: Dict[str, str] = {
    "inyeccion": "Usa consultas parametrizadas y ORMs. Nunca concatenes input del usuario en SQL.",
    "autenticacion": "Implementa MFA, bcrypt/argon2 para passwords, tokens de sesión seguros.",
    "xss": "Escapa siempre el output HTML. Usa Content Security Policy (CSP).",
    "ssrf": "Valida y filtra todas las URLs de destino. Usa allowlists de IPs.",
    "deserializacion": "Nunca deserialices datos no confiables. Valida firmas digitales.",
    "componentes": "Mantén dependencias actualizadas. Usa 'pip audit' o 'npm audit'.",
    "criptografia": "Usa AES-256, RSA-4096 o curvas elípticas. Nunca MD5 o SHA1 para passwords.",
}

_KEYWORDS_OWASP = {
    "sql": "inyeccion", "injection": "inyeccion", "inyeccion": "inyeccion",
    "login": "autenticacion", "autenticacion": "autenticacion", "password": "autenticacion",
    "xss": "xss", "cross site": "xss", "script": "xss",
    "ssrf": "ssrf", "request forgery": "ssrf",
    "deserializ": "deserializacion", "pickle": "deserializacion",
    "dependencia": "componentes", "libreria": "componentes", "package": "componentes",
    "cifrado": "criptografia", "encrypt": "criptografia", "hash": "criptografia",
}


class CybersecurityMCP:
    """
    MCP especializado en Ciberseguridad.
    - Búsqueda de CVEs en la NVD (NIST) API v2.0
    - Mejores prácticas OWASP Top 10 (local, sin latencia)
    """

    NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    TIMEOUT_S = 5

    def __init__(self):
        self.enabled = _REQUESTS_AVAILABLE

    def search_cve(self, cve_id: str) -> Optional[str]:
        """Busca un CVE específico en la base de datos NIST NVD."""
        if not self.enabled or not cve_id:
            return None

        cve_upper = cve_id.upper().strip()
        try:
            resp = requests.get(
                self.NVD_API_URL,
                params={"cveId": cve_upper},
                timeout=self.TIMEOUT_S,
                headers={"User-Agent": "Icaro-Assistant/1.0"},
            )
            if resp.ok:
                data = resp.json()
                vulns = data.get("vulnerabilities", [])
                if vulns:
                    cve_data = vulns[0].get("cve", {})
                    desc = next(
                        (d["value"] for d in cve_data.get("descriptions", []) if d["lang"] == "en"),
                        "Sin descripción disponible."
                    )
                    score = ""
                    metrics = cve_data.get("metrics", {})
                    for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
                        if key in metrics:
                            score = metrics[key][0]["cvssData"].get("baseScore", "")
                            break
                    
                    # Registrar en memoria compartida
                    log_event("CybersecurityMCP", "cve_searched", f"CVE {cve_upper} encontrado - Score: {score}")
                    
                    return f"CVE {cve_upper} (Score: {score}): {desc[:200]}"
                else:
                    log_event("CybersecurityMCP", "cve_searched", f"CVE {cve_upper} no encontrado")
                    return None
            return None
        except requests.exceptions.Timeout:
            logger.debug(f"[CybersecurityMCP] Timeout buscando {cve_id}")
            log_event("CybersecurityMCP", "cve_search_error", f"Timeout buscando {cve_upper}")
            return None
        except Exception as e:
            logger.debug(f"[CybersecurityMCP] Error: {e}")
            log_event("CybersecurityMCP", "cve_search_error", f"Error buscando {cve_upper}: {str(e)}")
            return None

    def get_security_best_practice(self, query: str) -> Optional[str]:
        """Retorna mejores prácticas OWASP relevantes para la consulta (sin latencia)."""
        q = query.lower()
        for keyword, category in _KEYWORDS_OWASP.items():
            if keyword in q:
                practice = _OWASP_TOP10.get(category)
                if practice:
                    # Registrar en memoria compartida
                    log_event("CybersecurityMCP", "practice_queried", f"Práctica OWASP: {category.capitalize()}")
                    return f"[OWASP - {category.capitalize()}] {practice}"
        return None

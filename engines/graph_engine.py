"""Relational Root Cause Analysis (RCA) Graph Engine.
Mengadopsi pola arsitektur maganghub.naufalhal.tech (NetworkX + Cytoscape.js export).
Menghubungkan entitas: Channel -> Vendor -> Incident -> FailureReason -> SOP.
"""

import networkx as nx
from typing import Dict, Any, List

class GraphRCAEngine:
    def __init__(self):
        self.G = nx.DiGraph()
        self._build_static_topology()
        
    def _build_static_topology(self):
        """Membangun simpul dan relasi dasar topologi perbankan & operasional."""
        # 1. Simpul Kanal (Channels)
        channels = [
            ("CH_VA_BCA", "VA_BCA", "Channel", "#3B82F6"),
            ("CH_VA_MANDIRI", "VA_MANDIRI", "Channel", "#3B82F6"),
            ("CH_QRIS_GOPAY", "QRIS_GOPAY", "Channel", "#06B6D4"),
            ("CH_CREDIT_CARD", "CREDIT_CARD", "Channel", "#8B5CF6"),
            ("CH_EWALLET_OVO", "EWALLET_OVO", "Channel", "#EC4899"),
        ]
        for node_id, label, n_type, color in channels:
            self.G.add_node(node_id, label=label, type=n_type, color=color, size=32)
            
        # 2. Simpul Vendor / Mitra Perbankan
        vendors = [
            ("VEN_BCA", "Bank Central Asia (BCA)", "Vendor", "#1E40AF"),
            ("VEN_MANDIRI", "Bank Mandiri", "Vendor", "#1E40AF"),
            ("VEN_ARTAJASA", "Artajasa / Switching Network", "Vendor", "#475569"),
            ("VEN_TELKOM", "Telkom Infra / Submarine FO", "Vendor", "#475569"),
        ]
        for node_id, label, n_type, color in vendors:
            self.G.add_node(node_id, label=label, type=n_type, color=color, size=36)
            
        # 3. Simpul Kode Kesalahan (Failure Codes)
        errors = [
            ("ERR_TIMEOUT", "ERR_GATEWAY_TIMEOUT", "ErrorCode", "#EF4444"),
            ("ERR_MALFUNCTION", "SYSTEM_MALFUNCTION", "ErrorCode", "#F97316"),
            ("ERR_FUNDS", "INSUFFICIENT_FUNDS", "ErrorCode", "#94A3B8"),
            ("ERR_PIN", "INVALID_PIN", "ErrorCode", "#94A3B8"),
        ]
        for node_id, label, n_type, color in errors:
            self.G.add_node(node_id, label=label, type=n_type, color=color, size=28)
            
        # 4. Simpul Dokumen Insiden Riil
        incidents = [
            ("INC_BCA_SWITCH", "#INC-20260912-BCA: DC Core Switch Migration", "Incident", "#DC2626"),
            ("INC_FO_TELKOM", "#INC-20260804-TELKOM: Submarine Cable Cut", "Incident", "#EA580C"),
            ("INC_KAFKA_LAG", "#INC-20260718-INTERNAL: Kafka Queue Lag", "Incident", "#D97706"),
        ]
        for node_id, label, n_type, color in incidents:
            self.G.add_node(node_id, label=label, type=n_type, color=color, size=40)
            
        # 5. Simpul Dokumen SOP Prosedural
        sops = [
            ("SOP_AUTOREFUND", "SOP-01: Auto-Refund & Reversal (30m)", "SOP", "#10B981"),
            ("SOP_L2_ESCALATION", "SOP-02: L2 Bank Contact & Maintenance Banner", "SOP", "#10B981"),
            ("SOP_FAILOVER", "SOP-03: L3 Circuit Breaker & Traffic Failover", "SOP", "#10B981"),
        ]
        for node_id, label, n_type, color in sops:
            self.G.add_node(node_id, label=label, type=n_type, color=color, size=34)
            
        # Relasi Statis (Edges)
        edges = [
            # Channel -> Vendor
            ("CH_VA_BCA", "VEN_BCA", "ROUTES_VIA"),
            ("CH_VA_MANDIRI", "VEN_MANDIRI", "ROUTES_VIA"),
            ("CH_QRIS_GOPAY", "VEN_ARTAJASA", "ROUTES_VIA"),
            ("CH_CREDIT_CARD", "VEN_TELKOM", "ROUTES_VIA"),
            
            # Incident -> Vendor / Channel
            ("INC_BCA_SWITCH", "VEN_BCA", "AFFECTS"),
            ("INC_BCA_SWITCH", "ERR_TIMEOUT", "TRIGGERS"),
            ("INC_FO_TELKOM", "VEN_TELKOM", "AFFECTS"),
            ("INC_FO_TELKOM", "ERR_TIMEOUT", "TRIGGERS"),
            ("INC_KAFKA_LAG", "CH_QRIS_GOPAY", "AFFECTS"),
            ("INC_KAFKA_LAG", "ERR_MALFUNCTION", "TRIGGERS"),
            
            # ErrorCode -> SOP
            ("ERR_TIMEOUT", "SOP_L2_ESCALATION", "GOVERNED_BY"),
            ("ERR_TIMEOUT", "SOP_AUTOREFUND", "GOVERNED_BY"),
            ("ERR_MALFUNCTION", "SOP_FAILOVER", "GOVERNED_BY"),
        ]
        for src, dst, rel in edges:
            self.G.add_edge(src, dst, relation=rel)

    def get_cytoscape_elements(self, highlight_channel: str = None) -> List[Dict[str, Any]]:
        """Mengonversi NetworkX Graph ke format Cytoscape.js dengan highlight anomali."""
        elements = []
        
        # Hitung node yang perlu di-highlight jika ada target channel
        highlighted_nodes = set()
        if highlight_channel:
            ch_node = f"CH_{highlight_channel.upper()}"
            if ch_node in self.G:
                highlighted_nodes.add(ch_node)
                # Tambahkan tetangga langsung (vendor) dan insiden terkait
                for neighbor in self.G.neighbors(ch_node):
                    highlighted_nodes.add(neighbor)
                for pred in self.G.predecessors(ch_node):
                    highlighted_nodes.add(pred)
                # Khusus BCA
                if "BCA" in highlight_channel:
                    highlighted_nodes.update(["INC_BCA_SWITCH", "ERR_TIMEOUT", "SOP_L2_ESCALATION", "SOP_AUTOREFUND"])
                    
        for node_id, data in self.G.nodes(data=True):
            is_active = (node_id in highlighted_nodes) if highlight_channel else False
            elements.append({
                "data": {
                    "id": node_id,
                    "label": data.get("label", node_id),
                    "type": data.get("type", "Generic"),
                    "color": "#FF2A55" if is_active and data.get("type") in ["Channel", "Incident"] else data.get("color", "#64748B"),
                    "size": (data.get("size", 30) + 12) if is_active else data.get("size", 30),
                    "is_active": is_active
                }
            })
            
        for src, dst, data in self.G.edges(data=True):
            is_active_edge = (src in highlighted_nodes and dst in highlighted_nodes) if highlight_channel else False
            elements.append({
                "data": {
                    "id": f"{src}_{dst}",
                    "source": src,
                    "target": dst,
                    "label": data.get("relation", ""),
                    "color": "#FF2A55" if is_active_edge else "rgba(148, 163, 184, 0.25)",
                    "width": 3 if is_active_edge else 1
                }
            })
            
        return elements

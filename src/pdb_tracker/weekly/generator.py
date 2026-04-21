#!/usr/bin/env python3
"""PDB Tracker - Weekly Report Generator

This module handles weekly PDB structure data fetching and report generation.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
import sqlite3
import logging
import requests
from abc import ABC, abstractmethod

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PDBEntry:
    """Represents a single PDB structure entry."""
    pdb_id: str
    title: str
    method: str
    resolution: Optional[float]
    release_date: str
    deposition_date: str
    ligands: List[str]
    journal: str
    doi: str
    authors: List[str]
    organism: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'pdb_id': self.pdb_id,
            'title': self.title,
            'method': self.method,
            'resolution': self.resolution,
            'release_date': self.release_date,
            'deposition_date': self.deposition_date,
            'ligands': self.ligands,
            'journal': self.journal,
            'doi': self.doi,
            'authors': self.authors,
            'organism': self.organism
        }


class PDBFetcher(ABC):
    """Abstract base class for PDB data fetching."""
    
    @abstractmethod
    def fetch_weekly(self, week_start: datetime, week_end: datetime) -> List[PDBEntry]:
        """Fetch PDB structures released in a given week."""
        pass
    
    @abstractmethod
    def fetch_by_id(self, pdb_id: str) -> Optional[PDBEntry]:
        """Fetch specific PDB structure by ID."""
        pass


class RCSBFetcher(PDBFetcher):
    """Fetches data from RCSB PDB REST API."""
    
    BASE_URL = "https://data.rcsb.org/rest/v1/core"
    SEARCH_URL = "https://search.rcsb.org/rcsbsearch/v2/query"
    
    def __init__(self, cache_dir: Optional[Path] = None):
        self.session = requests.Session()
        self.cache_dir = cache_dir or Path.home() / ".pdb_tracker" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def fetch_weekly(self, week_start: datetime, week_end: datetime) -> List[PDBEntry]:
        """Fetch structures released between week_start and week_end."""
        query = {
            "query": {
                "type": "group",
                "nodes": [
                    {
                        "type": "terminal",
                        "service": "text",
                        "parameters": {
                            "attribute": "rcsb_accession_info.initial_release_date",
                            "operator": "range",
                            "value": {
                                "from": week_start.strftime("%Y-%m-%d"),
                                "to": week_end.strftime("%Y-%m-%d")
                            }
                        }
                    }
                ],
                "logical_operator": "and"
            },
            "return_type": "entry",
            "request_options": {
                "return_all_hits": True
            }
        }
        
        try:
            response = self.session.post(
                self.SEARCH_URL,
                json=query,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            
            entries = []
            for result in data.get("result_set", []):
                pdb_id = result.get("identifier")
                if pdb_id:
                    entry = self._fetch_entry_details(pdb_id)
                    if entry:
                        entries.append(entry)
                        
            logger.info(f"Fetched {len(entries)} entries from RCSB PDB")
            return entries
            
        except Exception as e:
            logger.error(f"Failed to fetch weekly data: {e}")
            return []
    
    def fetch_by_id(self, pdb_id: str) -> Optional[PDBEntry]:
        """Fetch specific PDB entry details."""
        return self._fetch_entry_details(pdb_id)
    
    def _fetch_entry_details(self, pdb_id: str) -> Optional[PDBEntry]:
        """Fetch detailed information for a PDB entry."""
        cache_file = self.cache_dir / f"{pdb_id.lower()}.json"
        
        # Check cache
        if cache_file.exists():
            try:
                with open(cache_file) as f:
                    data = json.load(f)
                return self._parse_entry(data)
            except Exception:
                pass
        
        try:
            url = f"{self.BASE_URL}/entry/{pdb_id.upper()}"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Cache the response
            with open(cache_file, 'w') as f:
                json.dump(data, f)
            
            return self._parse_entry(data)
            
        except Exception as e:
            logger.error(f"Failed to fetch {pdb_id}: {e}")
            return None
    
    def _parse_entry(self, data: Dict[str, Any]) -> PDBEntry:
        """Parse RCSB API response into PDBEntry."""
        entry_id = data.get("rcsb_id", "")
        
        # Extract method
        methods = data.get("exptl", [])
        method = methods[0].get("method", "") if methods else "Unknown"
        
        # Extract resolution
        resolution = None
        if "refine" in data and data["refine"]:
            resolution = data["refine"][0].get("ls_d_res_high")
        elif "em_3d_reconstruction" in data:
            resolution = data["em_3d_reconstruction"][0].get("resolution")
        
        # Extract dates
        acc_info = data.get("rcsb_accession_info", {})
        release_date = acc_info.get("initial_release_date", "")
        deposition_date = acc_info.get("deposition_date", "")
        
        # Extract publication info
        pub_info = data.get("rcsb_primary_citation", {})
        journal = pub_info.get("journal_abbrev", "")
        doi = pub_info.get("pdbx_database_id_DOI", "")
        
        # Extract authors
        authors = []
        author_list = data.get("audit_author", [])
        for author in author_list:
            name = author.get("name", "")
            if name:
                authors.append(name)
        
        # Extract ligands
        ligands = []
        chem_comps = data.get("chem_comp", [])
        for comp in chem_comps:
            lig_id = comp.get("chem_comp", {}).get("id", "")
            if lig_id and lig_id not in ["HOH", "DOD"]:
                ligands.append(lig_id)
        
        # Extract organism
        organism = ""
        src_gen = data.get("entity_src_gen", [])
        if src_gen:
            organism = src_gen[0].get("ncbi_taxonomy_name", "")
        
        return PDBEntry(
            pdb_id=entry_id,
            title=data.get("struct", {}).get("title", ""),
            method=method,
            resolution=float(resolution) if resolution else None,
            release_date=release_date,
            deposition_date=deposition_date,
            ligands=ligands,
            journal=journal,
            doi=doi,
            authors=authors[:5],  # Limit to first 5 authors
            organism=organism
        )


class WeeklyReportGenerator:
    """Generates weekly PDB structure reports."""
    
    def __init__(self, db_path: Path, output_dir: Path, fetcher: Optional[PDBFetcher] = None):
        self.db_path = db_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.fetcher = fetcher or RCSBFetcher()
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weekly_snapshots (
                week_id TEXT PRIMARY KEY,
                week_start TEXT,
                week_end TEXT,
                total_structures INTEGER,
                cryoem_count INTEGER,
                xray_count INTEGER,
                nmr_count INTEGER,
                created_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weekly_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_id TEXT,
                pdb_id TEXT,
                method TEXT,
                resolution REAL,
                release_date TEXT,
                title TEXT,
                journal TEXT,
                journal_if REAL,
                FOREIGN KEY (week_id) REFERENCES weekly_snapshots(week_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def generate_report(self, week_id: str = None) -> Path:
        """Generate report for specified week (or current week if not specified)."""
        if week_id is None:
            week_id = datetime.now().strftime("%Y-W%W")
        
        # Parse week_id
        year, week = week_id.split("-W")
        year = int(year)
        week = int(week)
        
        # Calculate week boundaries
        # ISO week starts on Monday
        jan1 = datetime(year, 1, 1)
        week_start = jan1 + timedelta(days=(week - 1) * 7 - jan1.weekday())
        week_end = week_start + timedelta(days=7)
        
        logger.info(f"Generating report for week {week_id}: {week_start.date()} to {week_end.date()}")
        
        # Fetch data
        entries = self.fetcher.fetch_weekly(week_start, week_end)
        
        # Save to database
        self._save_to_db(week_id, week_start, week_end, entries)
        
        # Generate markdown report
        report_path = self._generate_markdown(week_id, week_start, week_end, entries)
        
        logger.info(f"Report generated: {report_path}")
        return report_path
    
    def _save_to_db(self, week_id: str, week_start: datetime, week_end: datetime, entries: List[PDBEntry]):
        """Save entries to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Count by method
        cryoem_count = sum(1 for e in entries if self._is_cryoem(e.method))
        xray_count = sum(1 for e in entries if self._is_xray(e.method))
        nmr_count = sum(1 for e in entries if self._is_nmr(e.method))
        
        # Insert snapshot
        cursor.execute("""
            INSERT OR REPLACE INTO weekly_snapshots
            (week_id, week_start, week_end, total_structures, cryoem_count, xray_count, nmr_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            week_id,
            week_start.strftime("%Y-%m-%d"),
            week_end.strftime("%Y-%m-%d"),
            len(entries),
            cryoem_count,
            xray_count,
            nmr_count,
            datetime.now().isoformat()
        ))
        
        # Delete old entries for this week
        cursor.execute("DELETE FROM weekly_entries WHERE week_id = ?", (week_id,))
        
        # Insert entries
        for entry in entries:
            cursor.execute("""
                INSERT INTO weekly_entries
                (week_id, pdb_id, method, resolution, release_date, title, journal)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                week_id,
                entry.pdb_id,
                entry.method,
                entry.resolution,
                entry.release_date,
                entry.title,
                entry.journal
            ))
        
        conn.commit()
        conn.close()
    
    def _generate_markdown(self, week_id: str, week_start: datetime, week_end: datetime, 
                          entries: List[PDBEntry]) -> Path:
        """Generate markdown report."""
        report_path = self.output_dir / f"PDB_Weekly_Report_{week_id}.md"
        
        cryoem_count = sum(1 for e in entries if self._is_cryoem(e.method))
        xray_count = sum(1 for e in entries if self._is_xray(e.method))
        nmr_count = sum(1 for e in entries if self._is_nmr(e.method))
        
        lines = [
            f"# PDB Weekly Report: {week_id}",
            "",
            f"**Period:** {week_start.strftime('%Y-%m-%d')} - {week_end.strftime('%Y-%m-%d')}",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "---",
            "",
            "## Summary",
            "",
            f"- **Total Structures:** {len(entries)}",
            f"- **Cryo-EM:** {cryoem_count}",
            f"- **X-ray:** {xray_count}",
            f"- **NMR:** {nmr_count}",
            "",
            "---",
            "",
            "## New Structures",
            "",
            "| PDB ID | Method | Resolution | Title |",
            "|--------|--------|------------|-------|",
        ]
        
        for entry in entries:
            res_str = f"{entry.resolution:.2f} Å" if entry.resolution else "N/A"
            title_short = entry.title[:60] + "..." if len(entry.title) > 60 else entry.title
            lines.append(f"| {entry.pdb_id} | {entry.method} | {res_str} | {title_short} |")
        
        lines.extend(["", "---", "", "*Generated by PDB Tracker*"])
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        return report_path
    
    @staticmethod
    def _is_cryoem(method: str) -> bool:
        method_lower = method.lower()
        return 'electron microscopy' in method_lower or 'cryo' in method_lower
    
    @staticmethod
    def _is_xray(method: str) -> bool:
        return 'x-ray' in method.lower() or 'xray' in method.lower()
    
    @staticmethod
    def _is_nmr(method: str) -> bool:
        return 'nmr' in method.lower()


if __name__ == "__main__":
    from pdb_tracker import config
    config.ensure_dirs()
    generator = WeeklyReportGenerator(
        db_path=config.get_db_path(),
        output_dir=config.get_weekly_reports_dir(),
    )
    report_path = generator.generate_report()
    print(f"Report generated: {report_path}")

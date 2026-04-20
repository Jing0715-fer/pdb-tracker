#!/usr/bin/env python3
"""PDB Tracker - Target Evaluation Module

This module handles protein target structure feasibility evaluation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import json
import sqlite3
import logging
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class UniProtEntry:
    """Represents UniProt protein entry."""
    uniprot_id: str
    entry_name: str
    protein_name: str
    gene_names: List[str]
    organism: str
    sequence_length: int
    sequence: str = ""
    keywords: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'uniprot_id': self.uniprot_id,
            'entry_name': self.entry_name,
            'protein_name': self.protein_name,
            'gene_names': self.gene_names,
            'organism': self.organism,
            'sequence_length': self.sequence_length,
            'keywords': self.keywords,
            'functions': self.functions
        }


@dataclass
class PDBStructure:
    """Represents PDB structure associated with UniProt entry."""
    pdb_id: str
    method: str
    resolution: Optional[float]
    title: str
    release_date: str
    deposition_date: str
    ligand: str
    journal: str
    journal_if: Optional[float]
    coverage: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'pdb_id': self.pdb_id,
            'method': self.method,
            'resolution': self.resolution,
            'title': self.title,
            'release_date': self.release_date,
            'deposition_date': self.deposition_date,
            'ligand': self.ligand,
            'journal': self.journal,
            'journal_if': self.journal_if,
            'coverage': self.coverage
        }


@dataclass
class FeasibilityScore:
    """Structure feasibility score for a method."""
    method: str
    score: int  # 0-10
    assessment: str
    rationale: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'method': self.method,
            'score': self.score,
            'assessment': self.assessment,
            'rationale': self.rationale
        }


class UniProtFetcher:
    """Fetches protein data from UniProt API."""
    
    BASE_URL = "https://rest.uniprot.org/uniprotkb"
    
    def __init__(self, cache_dir: Optional[Path] = None):
        self.session = requests.Session()
        self.cache_dir = cache_dir or Path.home() / ".pdb_tracker" / "uniprot_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def fetch(self, uniprot_id: str) -> Optional[UniProtEntry]:
        """Fetch UniProt entry by ID."""
        cache_file = self.cache_dir / f"{uniprot_id.upper()}.json"
        
        # Check cache
        if cache_file.exists():
            try:
                mtime = cache_file.stat().st_mtime
                age_days = (datetime.now().timestamp() - mtime) / 86400
                if age_days < 30:  # Cache valid for 30 days
                    with open(cache_file) as f:
                        data = json.load(f)
                    return self._parse_entry(uniprot_id, data)
            except Exception:
                pass
        
        try:
            url = f"{self.BASE_URL}/{uniprot_id.upper()}?format=json"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Cache the response
            with open(cache_file, 'w') as f:
                json.dump(data, f)
            
            return self._parse_entry(uniprot_id, data)
            
        except Exception as e:
            logger.error(f"Failed to fetch UniProt {uniprot_id}: {e}")
            return None
    
    def _parse_entry(self, uniprot_id: str, data: Dict[str, Any]) -> UniProtEntry:
        """Parse UniProt JSON response."""
        # Extract protein name
        protein_name = ""
        pd = data.get('proteinDescription', {})
        if 'recommendedName' in pd:
            protein_name = pd['recommendedName'].get('fullName', {}).get('value', '')
        
        # Extract gene names
        gene_names = []
        for gene in data.get('genes', []):
            if 'geneName' in gene:
                gene_names.append(gene['geneName'].get('value', ''))
        
        # Extract organism
        organism = data.get('organism', {}).get('scientificName', '')
        
        # Extract sequence length
        seq_length = data.get('sequence', {}).get('length', 0)
        sequence = data.get('sequence', {}).get('sequence', '')
        
        # Extract keywords
        keywords = [kw.get('keyword', {}).get('value', '') for kw in data.get('keywords', [])]
        
        # Extract functions
        functions = []
        for comment in data.get('comments', []):
            if comment.get('commentType') == 'FUNCTION':
                text = comment.get('texts', [{}])[0].get('value', '')
                if text:
                    functions.append(text)
        
        return UniProtEntry(
            uniprot_id=uniprot_id,
            entry_name=data.get('uniProtkbId', ''),
            protein_name=protein_name,
            gene_names=gene_names,
            organism=organism,
            sequence_length=seq_length,
            sequence=sequence,
            keywords=keywords,
            functions=functions
        )


class TargetEvaluator:
    """Evaluates protein target structure feasibility."""
    
    def __init__(self, db_path: Path, output_dir: Path, 
                 uniprot_fetcher: Optional[UniProtFetcher] = None,
                 pdb_fetcher=None):
        self.db_path = db_path
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.uniprot_fetcher = uniprot_fetcher or UniProtFetcher()
        self.pdb_fetcher = pdb_fetcher
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluations (
                uniprot_id TEXT PRIMARY KEY,
                entry_name TEXT,
                protein_name TEXT,
                gene_names TEXT,
                organism TEXT,
                sequence_length INTEGER,
                coverage REAL,
                scores TEXT,
                report TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluation_pdb_structures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uniprot_id TEXT,
                pdb_id TEXT,
                method TEXT,
                resolution REAL,
                title TEXT,
                release_date TEXT,
                ligand TEXT,
                journal TEXT,
                journal_if REAL,
                if_tier TEXT,
                updated_at TEXT,
                FOREIGN KEY (uniprot_id) REFERENCES evaluations(uniprot_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def evaluate(self, uniprot_id: str, force_refresh: bool = False) -> Path:
        """Evaluate protein target and generate report."""
        logger.info(f"Evaluating target: {uniprot_id}")
        
        # Check if already exists
        if not force_refresh and self._evaluation_exists(uniprot_id):
            logger.info(f"Evaluation for {uniprot_id} already exists. Use force_refresh=True to regenerate.")
            return self._get_report_path(uniprot_id)
        
        # Fetch UniProt data
        uniprot_entry = self.uniprot_fetcher.fetch(uniprot_id)
        if not uniprot_entry:
            raise ValueError(f"Failed to fetch UniProt data for {uniprot_id}")
        
        # Fetch PDB structures
        pdb_structures = self._fetch_pdb_structures(uniprot_id)
        
        # Calculate coverage
        coverage = self._calculate_coverage(uniprot_entry.sequence_length, pdb_structures)
        
        # Calculate feasibility scores
        scores = self._calculate_scores(uniprot_entry, pdb_structures)
        
        # Save to database
        self._save_evaluation(uniprot_entry, pdb_structures, coverage, scores)
        
        # Generate report
        report_path = self._generate_report(uniprot_entry, pdb_structures, coverage, scores)
        
        logger.info(f"Evaluation complete: {report_path}")
        return report_path
    
    def _evaluation_exists(self, uniprot_id: str) -> bool:
        """Check if evaluation exists in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM evaluations WHERE uniprot_id = ?", (uniprot_id,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    
    def _get_report_path(self, uniprot_id: str) -> Path:
        """Get path to existing report."""
        return self.output_dir / f"{uniprot_id}_结构可行性评估.md"
    
    def _fetch_pdb_structures(self, uniprot_id: str) -> List[PDBStructure]:
        """Fetch PDB structures associated with UniProt ID."""
        # This would use RCSB search API to find structures
        # For now, simplified implementation
        structures = []
        
        try:
            # Search RCSB for structures with this UniProt ID
            query = {
                "query": {
                    "type": "terminal",
                    "service": "text",
                    "parameters": {
                        "attribute": "rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_accession",
                        "operator": "exact_match",
                        "value": uniprot_id
                    }
                },
                "return_type": "entry",
                "request_options": {"return_all_hits": True}
            }
            
            response = requests.post(
                "https://search.rcsb.org/rcsbsearch/v2/query",
                json=query,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            
            for result in data.get("result_set", []):
                pdb_id = result.get("identifier")
                if pdb_id:
                    # Fetch detailed structure info
                    structure = self._fetch_structure_details(pdb_id)
                    if structure:
                        structures.append(structure)
            
            logger.info(f"Found {len(structures)} PDB structures for {uniprot_id}")
            
        except Exception as e:
            logger.error(f"Failed to fetch PDB structures: {e}")
        
        return structures
    
    def _fetch_structure_details(self, pdb_id: str) -> Optional[PDBStructure]:
        """Fetch detailed structure information."""
        try:
            url = f"https://data.rcsb.org/rest/v1/core/entry/{pdb_id}"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Extract method
            methods = data.get("exptl", [])
            method = methods[0].get("method", "Unknown") if methods else "Unknown"
            
            # Extract resolution
            resolution = None
            if "refine" in data and data["refine"]:
                resolution = data["refine"][0].get("ls_d_res_high")
            elif "em_3d_reconstruction" in data:
                resolution = data["em_3d_reconstruction"][0].get("resolution")
            
            # Extract publication info
            pub_info = data.get("rcsb_primary_citation", {})
            journal = pub_info.get("journal_abbrev", "")
            
            # Calculate journal IF tier
            journal_if = self._get_journal_if(journal)
            
            return PDBStructure(
                pdb_id=pdb_id,
                method=method,
                resolution=float(resolution) if resolution else None,
                title=data.get("struct", {}).get("title", ""),
                release_date=data.get("rcsb_accession_info", {}).get("initial_release_date", ""),
                deposition_date=data.get("rcsb_accession_info", {}).get("deposition_date", ""),
                ligand="",
                journal=journal,
                journal_if=journal_if
            )
            
        except Exception as e:
            logger.error(f"Failed to fetch structure details for {pdb_id}: {e}")
            return None
    
    def _get_journal_if(self, journal: str) -> Optional[float]:
        """Get journal impact factor."""
        # Simplified IF map - in production would use a database
        IF_MAP = {
            'Science': 56.9,
            'Nature': 43.1,
            'Cell': 45.5,
            'Cell Res.': 44.1,
            'Nat. Struct. Mol. Biol.': 18.0,
            'Nat Commun': 17.7,
            'Nucleic Acids Res.': 19.2,
            'Proc. Natl. Acad. Sci. USA': 11.1,
            'J. Am. Chem. Soc.': 15.0,
            'Structure': 4.4,
        }
        
        for key, value in IF_MAP.items():
            if key.lower() in journal.lower():
                return value
        return None
    
    def _calculate_coverage(self, sequence_length: int, structures: List[PDBStructure]) -> float:
        """Calculate sequence coverage from PDB structures."""
        # Simplified coverage calculation
        # In production would use SIFTS or similar to get actual coverage
        if not structures or sequence_length == 0:
            return 0.0
        
        # Rough estimate: assume each structure covers ~100-200 residues
        # This is a simplification - real implementation would parse PDB files
        estimated_coverage = min(100.0, len(structures) * 15.0)
        return round(estimated_coverage, 1)
    
    def _calculate_scores(self, uniprot_entry: UniProtEntry, 
                         structures: List[PDBStructure]) -> List[FeasibilityScore]:
        """Calculate structure feasibility scores."""
        scores = []
        seq_len = uniprot_entry.sequence_length
        
        # Group structures by method
        cryoem = [s for s in structures if 'cryo' in s.method.lower()]
        xray = [s for s in structures if 'x-ray' in s.method.lower()]
        nmr = [s for s in structures if 'nmr' in s.method.lower()]
        
        # Cryo-EM score
        cryoem_score = self._score_cryoem(seq_len, cryoem)
        scores.append(cryoem_score)
        
        # X-ray score
        xray_score = self._score_xray(seq_len, xray)
        scores.append(xray_score)
        
        # NMR score
        nmr_score = self._score_nmr(seq_len, nmr)
        scores.append(nmr_score)
        
        return scores
    
    def _score_cryoem(self, seq_len: int, structures: List[PDBStructure]) -> FeasibilityScore:
        """Calculate Cryo-EM feasibility score."""
        score = 5  # Base score
        
        # Size factor
        if seq_len > 1000:
            score += 3  # Large proteins good for Cryo-EM
        elif seq_len > 500:
            score += 2
        elif seq_len > 200:
            score += 1
        else:
            score -= 1  # Small proteins may be challenging
        
        # Previous success
        if structures:
            best_res = min((s.resolution for s in structures if s.resolution), default=None)
            if best_res and best_res < 3.0:
                score += 2
            elif best_res and best_res < 4.0:
                score += 1
        
        score = max(1, min(10, score))
        
        assessment = "推荐" if score >= 7 else "可行" if score >= 5 else "困难"
        
        return FeasibilityScore(
            method="Cryo-EM",
            score=score,
            assessment=assessment,
            rationale=f"Based on protein size ({seq_len} aa) and {len(structures)} existing structures"
        )
    
    def _score_xray(self, seq_len: int, structures: List[PDBStructure]) -> FeasibilityScore:
        """Calculate X-ray crystallography feasibility score."""
        score = 5  # Base score
        
        # Size factor
        if 100 < seq_len < 400:
            score += 3  # Ideal size range for crystallography
        elif 400 <= seq_len < 600:
            score += 1
        elif seq_len >= 800:
            score -= 2  # Large proteins challenging
        
        # Previous success
        if structures:
            best_res = min((s.resolution for s in structures if s.resolution), default=None)
            if best_res and best_res < 2.0:
                score += 2
            elif best_res and best_res < 2.5:
                score += 1
            score = min(10, score + 1)  # Bonus for having structures
        
        score = max(1, min(10, score))
        
        assessment = "推荐" if score >= 7 else "可行" if score >= 5 else "困难"
        
        return FeasibilityScore(
            method="X-ray",
            score=score,
            assessment=assessment,
            rationale=f"Based on protein size ({seq_len} aa) and {len(structures)} existing structures"
        )
    
    def _score_nmr(self, seq_len: int, structures: List[PDBStructure]) -> FeasibilityScore:
        """Calculate NMR feasibility score."""
        score = 5  # Base score
        
        # Size factor - NMR limited to smaller proteins
        if seq_len < 150:
            score += 3
        elif seq_len < 250:
            score += 1
        elif seq_len < 350:
            score -= 1
        else:
            score -= 3  # Too large for NMR
        
        # Previous success
        if structures:
            score += 1
        
        score = max(1, min(10, score))
        
        assessment = "推荐" if score >= 7 else "可行" if score >= 5 else "困难"
        
        return FeasibilityScore(
            method="NMR",
            score=score,
            assessment=assessment,
            rationale=f"Based on protein size ({seq_len} aa) - NMR limited to <350 aa"
        )
    
    def _save_evaluation(self, uniprot_entry: UniProtEntry, 
                        structures: List[PDBStructure],
                        coverage: float, 
                        scores: List[FeasibilityScore]):
        """Save evaluation to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        # Save evaluation
        scores_json = json.dumps({s.method: s.to_dict() for s in scores})
        cursor.execute("""
            INSERT OR REPLACE INTO evaluations
            (uniprot_id, entry_name, protein_name, gene_names, organism, 
             sequence_length, coverage, scores, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            uniprot_entry.uniprot_id,
            uniprot_entry.entry_name,
            uniprot_entry.protein_name,
            ', '.join(uniprot_entry.gene_names),
            uniprot_entry.organism,
            uniprot_entry.sequence_length,
            coverage,
            scores_json,
            now,
            now
        ))
        
        # Delete old PDB structures
        cursor.execute("DELETE FROM evaluation_pdb_structures WHERE uniprot_id = ?", 
                      (uniprot_entry.uniprot_id,))
        
        # Save PDB structures
        for s in structures:
            if_tier = self._calculate_if_tier(s.journal_if)
            cursor.execute("""
                INSERT INTO evaluation_pdb_structures
                (uniprot_id, pdb_id, method, resolution, title, release_date, 
                 ligand, journal, journal_if, if_tier, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                uniprot_entry.uniprot_id,
                s.pdb_id,
                s.method,
                s.resolution,
                s.title,
                s.release_date,
                s.ligand,
                s.journal,
                s.journal_if,
                if_tier,
                now
            ))
        
        conn.commit()
        conn.close()
    
    def _calculate_if_tier(self, journal_if: Optional[float]) -> str:
        """Calculate impact factor tier."""
        if journal_if is None:
            return 'unknown'
        if journal_if >= 20:
            return 'top'
        elif journal_if >= 10:
            return 'high'
        elif journal_if >= 5:
            return 'mid'
        else:
            return 'low'
    
    def _generate_report(self, uniprot_entry: UniProtEntry,
                        structures: List[PDBStructure],
                        coverage: float,
                        scores: List[FeasibilityScore]) -> Path:
        """Generate evaluation report using template."""
        # This would use a proper template engine in production
        # For now, generating basic markdown
        
        report_path = self.output_dir / f"{uniprot_entry.uniprot_id}_结构可行性评估.md"
        
        lines = [
            f"# 蛋白结构解析可行性评估报告",
            "",
            f"**蛋白名称:** {uniprot_entry.protein_name} ({uniprot_entry.gene_names[0] if uniprot_entry.gene_names else ''})",
            f"**UniProt ID:** {uniprot_entry.uniprot_id} ({uniprot_entry.entry_name})",
            f"**基因名称:** {', '.join(uniprot_entry.gene_names) if uniprot_entry.gene_names else 'N/A'}",
            f"**物种:** {uniprot_entry.organism}",
            f"**序列长度:** {uniprot_entry.sequence_length} 氨基酸",
            f"**报告生成日期:** {datetime.now().strftime('%Y-%m-%d')}",
            "",
            "---",
            "",
            "## 执行摘要",
            "",
            f"该蛋白已有 {len(structures)} 个 PDB 结构，序列覆盖度为 {coverage}%。",
            "",
            "| 评估项目 | 结果 |",
            "|---------|------|",
        ]
        
        for score in scores:
            lines.append(f"| {score.method} | {score.score}/10 - {score.assessment} |")
        
        lines.extend([
            "",
            "---",
            "",
            "## PDB结构列表",
            "",
            "| PDB ID | 方法 | 分辨率 | 标题 |",
            "|--------|------|--------|-------|",
        ])
        
        for s in structures:
            res_str = f"{s.resolution:.2f} Å" if s.resolution else "N/A"
            title_short = s.title[:50] + "..." if len(s.title) > 50 else s.title
            lines.append(f"| {s.pdb_id} | {s.method} | {res_str} | {title_short} |")
        
        lines.extend(["", "---", "", "*Generated by PDB Tracker*"])
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        return report_path


if __name__ == "__main__":
    # Example usage
    evaluator = TargetEvaluator(
        db_path=Path("pdb_tracker.db"),
        output_dir=Path("evaluations")
    )
    report_path = evaluator.evaluate("P04637")  # TP53
    print(f"Report generated: {report_path}")

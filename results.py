"""Results management and output formatting."""

import csv
import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from crawler import DiscoveryResult
from validator import ValidationResult

logger = logging.getLogger(__name__)


class ResultsManager:
    """Manages collection and output of discovery and validation results."""

    def __init__(self):
        """Initialize results manager."""
        self.results: List[Dict[str, Any]] = []
        self.stats = {
            "total_domains": 0,
            "files_discovered": 0,
            "yaml_valid": 0,
            "spec_valid": 0,
            "useful": 0,
            "not_found": 0,
            "errors": 0,
        }

    def add_result(
        self,
        discovery: DiscoveryResult,
        validation: ValidationResult = None
    ):
        """
        Add a discovery and validation result.
        
        Args:
            discovery: DiscoveryResult from crawler
            validation: Optional ValidationResult from validator
        """
        self.stats["total_domains"] += 1
        
        # Build combined result
        result = {
            "domain": discovery.domain,
            "file_url": discovery.file_url,
            "file_format": discovery.file_format,
            "http_status": discovery.http_status,
            "http_outcome": discovery.http_outcome,
            "redirect_chain": ";".join(discovery.redirect_chain) if discovery.redirect_chain else "",
            "final_url": discovery.final_url,
            "error_message": discovery.error_message,
            "discovery_timestamp": discovery.discovery_timestamp,
            "response_time_ms": discovery.response_time_ms,
        }
        
        # Add validation results if available
        if validation:
            # Truncate long error messages for CSV readability
            yaml_error = validation.yaml_error
            if yaml_error and len(yaml_error) > 100:
                yaml_error = yaml_error[:97] + "..."
            
            result.update({
                "yaml_valid": validation.yaml_valid,
                "yaml_error": yaml_error,
                "spec_valid": validation.spec_valid,
                "spec_errors": ";".join(validation.spec_errors) if validation.spec_errors else "",
                "spec_warnings": ";".join(validation.spec_warnings) if validation.spec_warnings else "",
                "validator_exit_code": validation.validator_exit_code,
                "useful": validation.useful,
                "usefulness_score": validation.usefulness_score,
                "usefulness_issues": ";".join(validation.usefulness_issues) if validation.usefulness_issues else "",
                "validation_timestamp": validation.validation_timestamp,
            })
            
            # Update stats
            if discovery.http_outcome == "success":
                self.stats["files_discovered"] += 1
            if validation.yaml_valid:
                self.stats["yaml_valid"] += 1
            if validation.spec_valid:
                self.stats["spec_valid"] += 1
            if validation.useful:
                self.stats["useful"] += 1
        else:
            # No validation data
            result.update({
                "yaml_valid": False,
                "yaml_error": None,
                "spec_valid": False,
                "spec_errors": "",
                "spec_warnings": "",
                "validator_exit_code": None,
                "useful": False,
                "usefulness_score": 0,
                "usefulness_issues": "",
                "validation_timestamp": None,
            })
        
        # Update outcome stats
        if discovery.http_outcome == "not_found":
            self.stats["not_found"] += 1
        elif discovery.http_outcome in ["error", "timeout", "ssl_error", "connection_error"]:
            self.stats["errors"] += 1
        
        self.results.append(result)

    def save_csv(self, filepath: str):
        """
        Save results to CSV file.
        
        Args:
            filepath: Path to output CSV file
        """
        if not self.results:
            logger.warning("No results to save")
            return
        
        logger.info(f"Saving results to CSV: {filepath}")
        
        # Define column order
        columns = [
            "domain",
            "file_url",
            "file_format",
            "http_status",
            "http_outcome",
            "final_url",
            "redirect_chain",
            "response_time_ms",
            "yaml_valid",
            "yaml_error",
            "spec_valid",
            "spec_errors",
            "spec_warnings",
            "validator_exit_code",
            "useful",
            "usefulness_score",
            "usefulness_issues",
            "error_message",
            "discovery_timestamp",
            "validation_timestamp",
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            writer.writerows(self.results)
        
        logger.info(f"Saved {len(self.results)} results to {filepath}")

    def save_json(self, filepath: str):
        """
        Save results to JSON file with full details.
        
        Args:
            filepath: Path to output JSON file
        """
        if not self.results:
            logger.warning("No results to save")
            return
        
        logger.info(f"Saving results to JSON: {filepath}")
        
        output = {
            "metadata": {
                "generated_at": datetime.utcnow().isoformat(),
                "total_results": len(self.results),
                "statistics": self.stats,
            },
            "results": self.results
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved {len(self.results)} results to {filepath}")

    def save_checkpoint(self, filepath: str, last_processed_index: int):
        """
        Save checkpoint file for resume capability.
        
        Args:
            filepath: Path to checkpoint file
            last_processed_index: Index of last processed domain
        """
        checkpoint = {
            "last_processed_index": last_processed_index,
            "timestamp": datetime.utcnow().isoformat(),
            "results_count": len(self.results),
            "stats": self.stats,
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(checkpoint, f, indent=2)
        
        logger.debug(f"Saved checkpoint: {last_processed_index}")

    def load_checkpoint(self, filepath: str) -> int:
        """
        Load checkpoint file.
        
        Args:
            filepath: Path to checkpoint file
            
        Returns:
            Index to resume from, or 0 if no checkpoint
        """
        if not Path(filepath).exists():
            logger.info("No checkpoint file found, starting from beginning")
            return 0
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                checkpoint = json.load(f)
            
            index = checkpoint.get("last_processed_index", 0)
            logger.info(f"Resuming from checkpoint at index {index}")
            return index
            
        except Exception as e:
            logger.error(f"Error loading checkpoint: {e}")
            return 0

    def print_summary(self):
        """Print summary statistics to console."""
        print("\n" + "="*60)
        print("PUBLICCODE.YML DISCOVERY SUMMARY")
        print("="*60)
        print(f"Total domains checked:     {self.stats['total_domains']:>6}")
        print(f"Files discovered:          {self.stats['files_discovered']:>6}")
        print(f"Valid YAML syntax:         {self.stats['yaml_valid']:>6}")
        print(f"Spec-compliant:            {self.stats['spec_valid']:>6}")
        print(f"Useful (>= 60% score):     {self.stats['useful']:>6}")
        print(f"Not found (404):           {self.stats['not_found']:>6}")
        print(f"Errors/timeouts:           {self.stats['errors']:>6}")
        print("-"*60)
        
        if self.stats['total_domains'] > 0:
            discovery_rate = (self.stats['files_discovered'] / self.stats['total_domains']) * 100
            print(f"Discovery rate:            {discovery_rate:>5.2f}%")
            
            if self.stats['files_discovered'] > 0:
                quality_rate = (self.stats['useful'] / self.stats['files_discovered']) * 100
                print(f"Quality rate (of found):   {quality_rate:>5.2f}%")
        
        print("="*60 + "\n")

    def generate_report(self, output_dir: str = "."):
        """
        Generate a comprehensive markdown report.
        
        Args:
            output_dir: Directory to save report
        """
        report_path = Path(output_dir) / "ANALYSIS_REPORT.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# PublicCode.yml Discovery and Validation Report\n\n")
            f.write(f"**Generated:** {datetime.utcnow().isoformat()}\n\n")
            
            f.write("## Executive Summary\n\n")
            f.write(f"- **Total Domains Tested:** {self.stats['total_domains']}\n")
            f.write(f"- **Files Discovered:** {self.stats['files_discovered']}\n")
            f.write(f"- **Valid YAML:** {self.stats['yaml_valid']}\n")
            f.write(f"- **Spec-Compliant:** {self.stats['spec_valid']}\n")
            f.write(f"- **High Quality (Useful):** {self.stats['useful']}\n\n")
            
            f.write("## Methodology\n\n")
            f.write("This analysis tested each government domain for publiccode.yml files at:\n")
            f.write("- `/publiccode.yml`\n")
            f.write("- `/.well-known/publiccode.yml`\n")
            f.write("- `/publiccode.yaml`\n")
            f.write("- `/.well-known/publiccode.yaml`\n\n")
            
            f.write("Validation was performed in three layers:\n")
            f.write("1. **YAML Syntax** - Parseable YAML structure\n")
            f.write("2. **Spec Compliance** - Adherence to publiccode.yml v0.5.0 standard\n")
            f.write("3. **Usefulness** - Practical metadata quality assessment\n\n")
            
            f.write("## Key Findings\n\n")
            
            if self.stats['total_domains'] > 0:
                discovery_rate = (self.stats['files_discovered'] / self.stats['total_domains']) * 100
                f.write(f"- **Discovery Rate:** {discovery_rate:.2f}% of domains have publiccode.yml\n")
                
                if self.stats['files_discovered'] > 0:
                    valid_rate = (self.stats['spec_valid'] / self.stats['files_discovered']) * 100
                    quality_rate = (self.stats['useful'] / self.stats['files_discovered']) * 100
                    f.write(f"- **Validation Rate:** {valid_rate:.2f}% of discovered files are spec-compliant\n")
                    f.write(f"- **Quality Rate:** {quality_rate:.2f}% of discovered files are high quality\n")
            
            f.write("\n## Limitations\n\n")
            f.write("- This analysis only checks website root paths, not repository-level adoption\n")
            f.write("- Absence from website does not indicate non-adoption\n")
            f.write("- Network errors and timeouts may undercount actual adoption\n")
            f.write("- Quality assessment is based on configurable heuristics\n\n")
            
            f.write("## Reproducibility\n\n")
            f.write("All data, configuration, and code used for this analysis are available.\n")
            f.write("Results can be independently verified by rerunning the discovery tool.\n\n")
        
        logger.info(f"Generated analysis report: {report_path}")
        print(f"\nDetailed report saved to: {report_path}")

    def get_stats(self) -> Dict:
        """Get current statistics."""
        return self.stats.copy()

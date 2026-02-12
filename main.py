#!/usr/bin/env python3
"""
Main orchestrator for publiccode.yml discovery and validation research.

This tool systematically discovers, validates, and assesses publiccode.yml files
across European government domains.
"""

import argparse
import csv
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime

from tqdm import tqdm

import config
from crawler import PublicCodeCrawler
from validator import PublicCodeValidator
from results import ResultsManager


def setup_logging(log_file: str = None, verbose: bool = False):
    """
    Setup logging configuration.
    
    Args:
        log_file: Optional log file path
        verbose: Enable debug logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=level,
        format=config.LOG_FORMAT,
        handlers=handlers
    )


def load_domains(filepath: str) -> list:
    """
    Load domains from CSV file.
    
    Args:
        filepath: Path to CSV file with domains
        
    Returns:
        List of domain strings
    """
    domains = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            domain = row.get('gov_domain', '').strip()
            if domain:
                domains.append(domain)
    
    logging.info(f"Loaded {len(domains)} domains from {filepath}")
    return domains


def process_domain(domain: str, crawler: PublicCodeCrawler, validator: PublicCodeValidator):
    """
    Process a single domain: discover and validate.
    
    Args:
        domain: Domain to process
        crawler: PublicCodeCrawler instance
        validator: PublicCodeValidator instance
        
    Returns:
        Tuple of (DiscoveryResult, ValidationResult or None)
    """
    # Discovery phase
    discovery = crawler.discover(domain)
    
    # Validation phase (only if file was found)
    validation = None
    if discovery.http_outcome == "success" and discovery.content:
        file_format = discovery.file_format or 'publiccode.yml'
        validation = validator.validate(discovery.content, file_format, source_url=discovery.final_url)
    
    return discovery, validation


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Discover and validate publiccode.yml files across government domains",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all domains
  python main.py --input eu_gov_domains.csv --output results.csv
  
  # Test mode (first 10 domains)
  python main.py --input eu_gov_domains.csv --output test_results.csv --limit 10
  
  # Resume from checkpoint
  python main.py --input eu_gov_domains.csv --output results.csv --resume
  
  # Verbose logging
  python main.py --input eu_gov_domains.csv --output results.csv --verbose
        """
    )
    
    parser.add_argument(
        '--input',
        default='eu_gov_domains.csv',
        help='Input CSV file with gov_domain column (default: eu_gov_domains.csv)'
    )
    parser.add_argument(
        '--output',
        default='results.csv',
        help='Output CSV file for results (default: results.csv)'
    )
    parser.add_argument(
        '--output-json',
        help='Optional JSON output file (default: None)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of domains to process (for testing)'
    )
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from checkpoint file'
    )
    parser.add_argument(
        '--checkpoint-interval',
        type=int,
        default=100,
        help='Save checkpoint every N domains (default: 100)'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=config.MAX_CONCURRENT_REQUESTS,
        help=f'Number of concurrent workers (default: {config.MAX_CONCURRENT_REQUESTS})'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose debug logging'
    )
    parser.add_argument(
        '--log-file',
        help='Optional log file path'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_file, args.verbose)
    logger = logging.getLogger(__name__)
    
    # Print header
    print("\n" + "="*60)
    print("PUBLICCODE.YML DISCOVERY AND VALIDATION FRAMEWORK")
    print("="*60)
    print(f"Input: {args.input}")
    print(f"Output: {args.output}")
    if args.output_json:
        print(f"JSON Output: {args.output_json}")
    print(f"Workers: {args.workers}")
    if args.limit:
        print(f"Limit: {args.limit} domains")
    print("="*60 + "\n")
    
    # Load domains
    try:
        domains = load_domains(args.input)
    except Exception as e:
        logger.error(f"Failed to load domains: {e}")
        return 1
    
    # Apply limit if specified
    if args.limit:
        domains = domains[:args.limit]
        logger.info(f"Limited to {len(domains)} domains")
    
    # Initialize components
    crawler = PublicCodeCrawler()
    validator = PublicCodeValidator()
    results_manager = ResultsManager()
    
    # Check for resume
    start_index = 0
    if args.resume:
        start_index = results_manager.load_checkpoint(config.CHECKPOINT_FILE)
        domains = domains[start_index:]
        logger.info(f"Resuming from domain {start_index}")
    
    # Process domains
    print(f"\nProcessing {len(domains)} domains...\n")
    
    # Track progress for periodic updates
    last_summary_time = time.time()
    summary_interval = 60  # Print summary every 60 seconds
    processed_count = 0
    
    try:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(process_domain, domain, crawler, validator): (idx + start_index, domain)
                for idx, domain in enumerate(domains)
            }
            
            # Process results with progress bar
            with tqdm(total=len(domains), desc="Discovering", unit="domain", 
                     bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]') as pbar:
                for future in as_completed(futures):
                    idx, domain = futures[future]
                    
                    try:
                        discovery, validation = future.result()
                        results_manager.add_result(discovery, validation)
                        processed_count += 1
                        
                        # Update progress bar with current domain status
                        if discovery.http_outcome == "success":
                            pbar.set_postfix_str(f"✓ Found: {domain}", refresh=True)
                        
                        # Print periodic summary
                        current_time = time.time()
                        if current_time - last_summary_time >= summary_interval:
                            stats = results_manager.get_stats()
                            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Progress Update:")
                            print(f"  Processed: {stats['total_domains']:,} domains")
                            print(f"  Found: {stats['files_discovered']} files ({stats['files_discovered']/max(stats['total_domains'],1)*100:.1f}%)")
                            print(f"  Valid YAML: {stats['yaml_valid']} | Spec-compliant: {stats['spec_valid']} | Useful: {stats['useful']}")
                            print(f"  Errors/Timeouts: {stats['errors']}")
                            last_summary_time = current_time
                        
                        # Save checkpoint periodically
                        if (idx - start_index) % args.checkpoint_interval == 0:
                            results_manager.save_checkpoint(config.CHECKPOINT_FILE, idx)
                            results_manager.save_csv(args.output)
                            if args.output_json:
                                results_manager.save_json(args.output_json)
                        
                    except Exception as e:
                        logger.error(f"Error processing {domain}: {e}")
                    
                    pbar.update(1)
        
        # Final save
        logger.info("Saving final results...")
        results_manager.save_csv(args.output)
        if args.output_json:
            results_manager.save_json(args.output_json)
        
        # Generate report
        results_manager.generate_report()
        
        # Print summary
        results_manager.print_summary()
        
        # Print crawler stats
        crawler_stats = crawler.get_stats()
        print("Crawler Statistics:")
        print(f"  Domains checked: {crawler_stats['domains_checked']}")
        print(f"  Files found: {crawler_stats['files_found']}")
        print(f"  Timeouts: {crawler_stats['timeouts']}")
        print(f"  Errors: {crawler_stats['errors']}")
        print()
        
        print(f"✓ Results saved to: {args.output}")
        if args.output_json:
            print(f"✓ JSON saved to: {args.output_json}")
        print(f"✓ Report saved to: ANALYSIS_REPORT.md")
        print()
        
        return 0
        
    except KeyboardInterrupt:
        logger.warning("\nInterrupted by user. Saving partial results...")
        results_manager.save_csv(args.output)
        if args.output_json:
            results_manager.save_json(args.output_json)
        results_manager.save_checkpoint(config.CHECKPOINT_FILE, start_index + len(results_manager.results))
        print("\n\nPartial results saved. Use --resume to continue.")
        return 130
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

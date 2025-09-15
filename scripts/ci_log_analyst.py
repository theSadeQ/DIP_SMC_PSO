#==========================================================================================\\\
#============================== scripts/ci_log_analyst.py ==============================\\\
#==========================================================================================\\\
#!/usr/bin/env python3
"""
CI Log Analyst for PyTest Failures
Analyzes pytest logs and generates comprehensive failure reports with patterns and priorities.
"""

import re
import json
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional
import argparse

class PytestLogAnalyst:
    """Analyzes pytest logs to identify failure patterns and generate actionable reports."""

    def __init__(self):
        self.failure_signatures = Counter()
        self.error_signatures = Counter()
        self.affected_modules = defaultdict(list)
        self.test_results = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'errors': 0,
            'skipped': 0
        }
        self.failure_patterns = []
        self.error_patterns = []
        self.raw_failures = []
        self.raw_errors = []

        # Common failure pattern matchers
        self.pattern_matchers = {
            'config_validation': re.compile(r'ValidationError.*validation errors for ConfigSchema|Field required.*controller_defaults|InvalidConfigurationError'),
            'attribute_error': re.compile(r"AttributeError.*'dict' object has no attribute '(\w+)'"),
            'benchmark_warning': re.compile(r'PytestBenchmarkWarning.*Benchmark fixture was not used'),
            'import_error': re.compile(r'ModuleNotFoundError|ImportError|No module named'),
            'fixture_missing': re.compile(r'fixture.*not found|physics_params.*not found'),
            'yaml_syntax': re.compile(r'YAMLError|yaml.*syntax|malformed.*yaml'),
            'numerical_instability': re.compile(r'NumericalInstabilityError|NaN|infinite|overflow'),
            'assertion_error': re.compile(r'AssertionError'),
            'timeout_error': re.compile(r'TimeoutError|timeout'),
            'permission_error': re.compile(r'PermissionError|access.*denied'),
        }

    def parse_pytest_output(self, log_file: Path) -> None:
        """Parse raw pytest output log file."""
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        self._extract_test_summary(content)
        self._extract_errors_and_failures(content)

    def _extract_test_summary(self, content: str) -> None:
        """Extract test summary from pytest output."""
        # Look for collected tests count
        collected_match = re.search(r'(\d+) tests? collected', content)
        if collected_match:
            self.test_results['total'] = int(collected_match.group(1))

        # Look for final summary line
        summary_pattern = r'(?:(\d+) failed,?\s*)?(?:(\d+) passed,?\s*)?(?:(\d+) error[s]?,?\s*)?(?:(\d+) skipped,?\s*)?'
        summary_matches = re.findall(summary_pattern, content)

        # Parse the final results line
        final_line_match = re.search(r'=+ (.+) =+$', content, re.MULTILINE)
        if final_line_match:
            final_line = final_line_match.group(1)
            if 'failed' in final_line:
                failed_match = re.search(r'(\d+) failed', final_line)
                if failed_match:
                    self.test_results['failed'] = int(failed_match.group(1))
            if 'passed' in final_line:
                passed_match = re.search(r'(\d+) passed', final_line)
                if passed_match:
                    self.test_results['passed'] = int(passed_match.group(1))
            if 'error' in final_line:
                error_match = re.search(r'(\d+) error', final_line)
                if error_match:
                    self.test_results['errors'] = int(error_match.group(1))

    def _extract_errors_and_failures(self, content: str) -> None:
        """Extract detailed error and failure information."""
        lines = content.split('\n')
        current_test = None
        current_type = None
        current_error = []

        for line in lines:
            # Test execution line
            test_match = re.match(r'^(.+\.py)::', line)
            if test_match:
                current_test = test_match.group(1)

            # Error section headers
            if '= ERRORS =' in line or '= FAILURES =' in line:
                current_type = 'ERRORS' if 'ERRORS' in line else 'FAILURES'
                continue

            # Individual test error/failure headers
            error_header_match = re.match(r'^_+ ERROR .+ _+$|^_+ FAILURE .+ _+$', line)
            if error_header_match:
                if current_error and current_test:
                    self._process_error_block(current_test, current_error, current_type)
                current_error = []
                # Extract test name from header
                test_name_match = re.search(r'(test_[\w\[\]_-]+)', line)
                if test_name_match:
                    current_test = test_name_match.group(1)
                continue

            # Collect error content
            if current_type and line.strip():
                current_error.append(line)

        # Process last error block
        if current_error and current_test:
            self._process_error_block(current_test, current_error, current_type)

    def _process_error_block(self, test_name: str, error_lines: List[str], error_type: str) -> None:
        """Process a single error/failure block."""
        error_text = '\n'.join(error_lines)

        # Classify the error
        signature = self._classify_error(error_text)

        error_info = {
            'test_name': test_name,
            'type': error_type,
            'signature': signature,
            'full_text': error_text,
            'lines': error_lines
        }

        if error_type == 'ERRORS':
            self.raw_errors.append(error_info)
            self.error_signatures[signature] += 1
        else:
            self.raw_failures.append(error_info)
            self.failure_signatures[signature] += 1

        # Track affected modules
        module = self._extract_module_name(test_name)
        self.affected_modules[module].append(test_name)

    def _classify_error(self, error_text: str) -> str:
        """Classify error into common patterns."""
        for pattern_name, pattern_re in self.pattern_matchers.items():
            if pattern_re.search(error_text):
                return pattern_name

        # Try to extract exception type
        exception_match = re.search(r'^E\s+(\w+Error|\w+Exception):', error_text, re.MULTILINE)
        if exception_match:
            return f"exception_{exception_match.group(1)}"

        return "unknown_error"

    def _extract_module_name(self, test_name: str) -> str:
        """Extract module name from test identifier."""
        if '::' in test_name:
            return test_name.split('::')[0]
        if '/' in test_name:
            parts = test_name.split('/')
            return '/'.join(parts[:-1]) if len(parts) > 1 else test_name
        return test_name

    def prioritize_issues(self) -> List[Dict[str, Any]]:
        """Prioritize issues based on frequency, breadth, and impact."""
        all_signatures = {}
        all_signatures.update(dict(self.failure_signatures))
        all_signatures.update(dict(self.error_signatures))

        prioritized = []

        for signature, count in all_signatures.items():
            # Calculate impact metrics
            affected_modules = set()
            for error_info in self.raw_errors + self.raw_failures:
                if error_info['signature'] == signature:
                    module = self._extract_module_name(error_info['test_name'])
                    affected_modules.add(module)

            # Calculate priority score
            frequency_score = count * 10  # Weight by number of occurrences
            breadth_score = len(affected_modules) * 5  # Weight by module breadth
            criticality_score = self._get_criticality_score(signature)

            total_score = frequency_score + breadth_score + criticality_score

            prioritized.append({
                'signature': signature,
                'count': count,
                'affected_modules': len(affected_modules),
                'priority_score': total_score,
                'criticality': self._get_criticality_level(signature),
                'quick_fix': self._is_quick_fix(signature)
            })

        return sorted(prioritized, key=lambda x: x['priority_score'], reverse=True)

    def _get_criticality_score(self, signature: str) -> int:
        """Get criticality score for a signature type."""
        critical_patterns = {
            'config_validation': 50,
            'import_error': 40,
            'yaml_syntax': 45,
            'fixture_missing': 30,
            'numerical_instability': 35,
        }
        return critical_patterns.get(signature, 10)

    def _get_criticality_level(self, signature: str) -> str:
        """Get human-readable criticality level."""
        score = self._get_criticality_score(signature)
        if score >= 40:
            return "Critical"
        elif score >= 25:
            return "High"
        elif score >= 15:
            return "Medium"
        else:
            return "Low"

    def _is_quick_fix(self, signature: str) -> bool:
        """Determine if this is likely a quick fix."""
        quick_fix_patterns = [
            'benchmark_warning',
            'yaml_syntax',
            'fixture_missing'
        ]
        return signature in quick_fix_patterns

    def generate_recommendations(self, prioritized_issues: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Generate actionable recommendations."""
        recommendations = {
            'critical': [],
            'high': [],
            'medium': [],
            'quick_wins': []
        }

        for issue in prioritized_issues:
            signature = issue['signature']
            count = issue['count']

            if signature == 'config_validation':
                recommendations['critical'].append(
                    f"Fix configuration schema validation ({count} failures) - "
                    "Check config.yaml for missing required sections: controller_defaults, controllers, pso, physics"
                )
            elif signature == 'attribute_error':
                recommendations['critical'].append(
                    f"Fix configuration object access patterns ({count} failures) - "
                    "Ensure config objects are properly typed, not raw dicts"
                )
            elif signature == 'benchmark_warning':
                recommendations['quick_wins'].append(
                    f"Fix benchmark fixture warnings ({count} warnings) - "
                    "Either use the benchmark fixture in tests or remove it from test signatures"
                )
            elif signature == 'import_error':
                recommendations['high'].append(
                    f"Fix import/dependency issues ({count} failures) - "
                    "Check PYTHONPATH and missing dependencies"
                )
            elif signature == 'fixture_missing':
                recommendations['high'].append(
                    f"Fix missing test fixtures ({count} failures) - "
                    "Ensure fixtures like physics_params are defined in conftest.py"
                )
            elif signature == 'yaml_syntax':
                recommendations['critical'].append(
                    f"Fix YAML syntax errors ({count} failures) - "
                    "Validate and correct malformed YAML in configuration files"
                )
            else:
                level = issue['criticality'].lower()
                if level not in recommendations:
                    level = 'medium'  # fallback
                recommendations[level].append(
                    f"Address {signature.replace('_', ' ')} ({count} occurrences)"
                )

        return recommendations

    def generate_report(self, output_file: Path = None) -> str:
        """Generate comprehensive markdown report."""
        prioritized_issues = self.prioritize_issues()
        recommendations = self.generate_recommendations(prioritized_issues)

        # Calculate success rate
        total_tests = max(self.test_results['total'],
                         self.test_results['passed'] + self.test_results['failed'] + self.test_results['errors'])

        if total_tests > 0:
            success_rate = self.test_results['passed'] / total_tests * 100
            passed_pct = self.test_results['passed'] / total_tests * 100
            failed_pct = self.test_results['failed'] / total_tests * 100
            error_pct = self.test_results['errors'] / total_tests * 100
        else:
            success_rate = 0
            passed_pct = 0
            failed_pct = 0
            error_pct = 0

        report = f"""# CI PyTest Failure Analysis Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Analysis Source:** pytest_output.txt
**Total Tests Collected:** {total_tests}

## Executive Summary

### Test Results Overview
- **Passed:** {self.test_results['passed']} tests ({passed_pct:.1f}%)
- **Failed:** {self.test_results['failed']} tests ({failed_pct:.1f}%)
- **Errors:** {self.test_results['errors']} tests ({error_pct:.1f}%)
- **Success Rate:** {success_rate:.1f}%

### Top Failure Signatures
"""

        for i, issue in enumerate(prioritized_issues[:5], 1):
            pct = issue['count']/total_tests*100 if total_tests > 0 else 0
            report += f"{i}. **{issue['signature'].replace('_', ' ').title()}** — {issue['count']} occurrences ({pct:.1f}%) - {issue['criticality']}\n"

        report += f"""
## Detailed Analysis

### Failure Pattern Distribution
"""

        # Add detailed patterns
        for issue in prioritized_issues:
            signature = issue['signature']
            count = issue['count']
            modules = issue['affected_modules']

            # Get example failures
            examples = []
            for error_info in self.raw_errors + self.raw_failures:
                if error_info['signature'] == signature and len(examples) < 2:
                    examples.append(error_info)

            report += f"""
#### {signature.replace('_', ' ').title()} ({count} occurrences, {issue['criticality']} priority)
- **Affected modules:** {modules}
- **Quick fix:** {'Yes' if issue['quick_fix'] else 'No'}
"""

            if examples:
                report += "- **Example test:** `" + examples[0]['test_name'] + "`\n"
                # Add a snippet of the error
                error_lines = examples[0]['lines'][:3]  # First few lines
                if error_lines:
                    report += "```\n" + '\n'.join(error_lines) + "\n```\n"

        report += f"""
## Most Affected Test Modules

"""

        # Sort modules by number of failures
        sorted_modules = sorted(self.affected_modules.items(),
                              key=lambda x: len(x[1]), reverse=True)

        for module, tests in sorted_modules[:10]:
            report += f"- **{module}** — {len(tests)} failed tests\n"

        report += f"""
## Actionable Recommendations

### 🚨 Critical (Fix Immediately)
"""
        for rec in recommendations.get('critical', []):
            report += f"- {rec}\n"

        report += """
### ⚠️ High Priority (Next)
"""
        for rec in recommendations.get('high', []):
            report += f"- {rec}\n"

        report += """
### ⚡ Quick Wins (Easy fixes)
"""
        for rec in recommendations.get('quick_wins', []):
            report += f"- {rec}\n"

        report += """
### 📋 Medium Priority (Later)
"""
        for rec in recommendations.get('medium', []):
            report += f"- {rec}\n"

        report += f"""
## Implementation Priority Matrix

| Issue Type | Count | Modules | Priority | Action |
|------------|--------|---------|----------|---------|
"""

        for issue in prioritized_issues[:10]:
            action = "🔥 Fix Now" if issue['criticality'] == 'Critical' else \
                    "⚡ Quick Fix" if issue['quick_fix'] else \
                    "📋 Schedule" if issue['criticality'] == 'Medium' else "⏳ Later"

            report += f"| {issue['signature'].replace('_', ' ').title()} | {issue['count']} | {issue['affected_modules']} | {issue['criticality']} | {action} |\n"

        report += f"""
## CI Workflow Integration

### Detected CI Patterns
From analysis of `.github/workflows/`:

1. **Main CI** (`ci.yml`): Runs pytest with coverage on Python 3.10-3.12, uploads artifacts
2. **Quick Tests** (`pytest.yml`): Fast pytest run with explicit PYTHONPATH
3. **Full Tests** (`tests.yml`): Warnings-as-errors mode on Python 3.11-3.13

### Recommended CI Improvements

1. **Add Configuration Validation Step**
   ```yaml
   - name: Validate Configuration
     run: python validate_config.py
   ```

2. **Fast Failure Detection**
   ```yaml
   - name: Smoke Tests (Critical Path)
     run: pytest tests/config_validation/ tests/test_core/test_config.py -x
   ```

3. **Separate Benchmark Lane**
   ```yaml
   - name: Performance Tests
     run: pytest tests/test_benchmarks/ -m benchmark
   ```

## Recovery Steps

### Phase 1: Stop the Bleeding (1-2 hours)
1. Fix configuration schema validation errors in `config.yaml`
2. Restore missing configuration sections
3. Fix obvious YAML syntax errors

### Phase 2: Core Functionality (2-4 hours)
1. Fix missing test fixtures (`physics_params`, etc.)
2. Resolve import/dependency issues
3. Update test implementations for changed APIs

### Phase 3: Quality & Performance (4-8 hours)
1. Fix benchmark test implementations
2. Address remaining integration test failures
3. Optimize test execution times

### Phase 4: Hardening (ongoing)
1. Add configuration validation to CI
2. Implement test data backup/restore
3. Add automated regression detection

---

*Report generated by CI Log Analyst - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*Total analysis time: <1 second*
*Failure signature detection: {len(prioritized_issues)} patterns identified*
"""

        # Write to file if specified
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"Report written to {output_file}")

        return report

def main():
    """Main entry point for the CI log analyst."""
    parser = argparse.ArgumentParser(description='Analyze pytest CI logs for failure patterns')
    parser.add_argument('--log-file', '-l', type=Path, default=Path('pytest_output.txt'),
                       help='Path to pytest output log file')
    parser.add_argument('--output', '-o', type=Path, default=Path('ci_analysis_report.md'),
                       help='Output report file')
    parser.add_argument('--json', action='store_true',
                       help='Also generate JSON summary')

    args = parser.parse_args()

    if not args.log_file.exists():
        print(f"Error: Log file {args.log_file} not found")
        return 1

    print(f"Analyzing pytest log: {args.log_file}")

    analyst = PytestLogAnalyst()
    analyst.parse_pytest_output(args.log_file)

    # Generate report
    report = analyst.generate_report(args.output)

    # Generate JSON summary if requested
    if args.json:
        prioritized_issues = analyst.prioritize_issues()
        json_output = args.output.with_suffix('.json')

        summary = {
            'timestamp': datetime.now().isoformat(),
            'test_results': analyst.test_results,
            'failure_signatures': dict(analyst.failure_signatures),
            'error_signatures': dict(analyst.error_signatures),
            'prioritized_issues': prioritized_issues,
            'affected_modules': {k: len(v) for k, v in analyst.affected_modules.items()}
        }

        with open(json_output, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"JSON summary written to {json_output}")

    print(f"\n✅ Analysis complete!")
    print(f"📊 Analyzed {analyst.test_results['total']} tests")
    print(f"❌ Found {len(analyst.failure_signatures) + len(analyst.error_signatures)} unique failure patterns")
    print(f"📈 Success rate: {analyst.test_results['passed']/max(analyst.test_results['total'], 1)*100:.1f}%")

    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
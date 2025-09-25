# Core project files for human viewing
echo '=== MAIN PROJECT FILES ==='
echo '📁 Core:'
ls -1 src/ tests/ simulate.py streamlit_app.py config.yaml README.md 2>/dev/null | head -6
echo
echo '📁 Documentation:'  
ls -1 docs/ notebooks/ CHANGELOG.md 2>/dev/null | head -3
echo
echo '📁 Development:'
ls -1 scripts/ tools/ dev_tools/ benchmarks/ 2>/dev/null | head -4
echo
echo '📁 Configuration:'
ls -1 requirements.txt pytest.ini Makefile config/ 2>/dev/null | head -4
echo
echo '📁 Archive:'
ls -1 archive/ 2>/dev/null | head -1


# HRRR Maps v2.2 - Portable Setup Guide

This is a portable version of the HRRR Weather Model Processing System v2.2.
Follow these steps to set up on a new system.

## 📋 Requirements

### System Requirements
- Python 3.11 or later
- Conda (Miniconda or Anaconda)
- Git (for version control)
- ~2GB free disk space for dependencies
- Internet connection for downloading weather data

### Operating Systems
- Linux (Ubuntu, CentOS, etc.) - Recommended
- macOS
- Windows (with WSL2 recommended for best performance)

## 🚀 Quick Setup

### 1. Create Conda Environment
```bash
# Create new environment
conda create -n hrrr_maps python=3.11
conda activate hrrr_maps

# Install core scientific dependencies
conda install -c conda-forge cartopy cfgrib matplotlib xarray numpy pandas

# Install additional dependencies
pip install psutil requests

# Install CLI enhancement libraries (optional but recommended)
pip install rich typer questionary
```

### 2. Setup Project Directory
```bash
# Navigate to your desired location
cd /path/to/your/projects

# Copy the hrrr-maps folder here
# Then navigate into it
cd hrrr-maps

# Make CLI executable (Linux/macOS)
chmod +x processor_cli.py
```

### 3. Test Installation
```bash
# Test basic functionality
python processor_cli.py --help

# Run comprehensive test suite
python tests/run_all_tests.py

# Test parameter listing
python processor_cli.py --list-fields --category severe
```

### 4. First Data Processing Test
```bash
# Process latest HRRR run (small test)
python processor_cli.py --latest --fields sbcape --hours 0 --debug

# If successful, try a full category
python processor_cli.py --latest --categories severe --hours 0-3
```

## 📁 Directory Structure

```
hrrr-maps/
├── smart_hrrr/           # Core processing package
├── derived_params/       # Weather parameter calculations (108 parameters)
├── core/                 # GRIB loading, plotting, metadata
├── config/               # Color maps and styling
├── parameters/           # JSON parameter configurations
├── tools/                # Utilities and GIF creation
├── tests/                # Comprehensive test suite
├── processor_cli.py      # Main CLI interface
├── README.md            # Full project documentation
├── DERIVED_PARAMETERS_LATEST.md  # Latest parameter documentation
└── SETUP.md             # This setup guide
```

## ⚙️ Configuration

### Environment Variables (Optional)
```bash
# Disable parallel processing if needed
export HRRR_USE_PARALLEL=false

# Set custom number of workers
export HRRR_MAX_WORKERS=4

# Enable debug logging
export HRRR_DEBUG=1
```

### Custom Output Directory
```bash
# Process to custom directory
python processor_cli.py --latest --output-dir /path/to/custom/output
```

## 🎯 Quick Start Examples

### Severe Weather Analysis
```bash
# Latest tornado parameters (SPC-aligned)
python processor_cli.py --latest --fields stp_fixed,ehi_spc,cape_03km --hours 0-6

# Full severe weather suite
python processor_cli.py --latest --categories severe --hours 0-12 --workers 4
```

### Fire Weather Monitoring
```bash
# Current smoke and fire conditions
python processor_cli.py --latest --categories smoke,fire --hours 0-6
```

### Create Animations
```bash
cd tools
python create_gifs.py --latest --categories severe --max-hours 12 --duration 300
```

## 🧪 Validation

Run the comprehensive test suite to ensure everything is working:

```bash
# Run all tests
python tests/run_all_tests.py

# Run just v2.2 validation tests
python tests/run_all_tests.py --v22-only

# Expected output: "🎉 ALL TEST SUITES PASSED!"
```

## 🔧 Troubleshooting

### Common Issues

**1. Import Errors**
```bash
# Add project to Python path if needed
export PYTHONPATH="${PYTHONPATH}:/path/to/hrrr-maps"
```

**2. Missing Dependencies**
```bash
# Install missing cartopy dependencies on Ubuntu
sudo apt-get install libproj-dev proj-data proj-bin libgeos-dev

# On macOS
brew install proj geos
```

**3. GRIB Loading Issues**
```bash
# Ensure cfgrib is working
python -c "import cfgrib; print('cfgrib OK')"

# Test with debug mode
HRRR_DEBUG=1 python processor_cli.py --latest --fields t2m --hours 0
```

**4. Memory Issues**
```bash
# Reduce worker count
export HRRR_MAX_WORKERS=2

# Or disable parallel processing
export HRRR_USE_PARALLEL=false
```

## 📊 System Status

**Version**: HRRR v2.2 (Production Ready)
**Total Parameters**: 108 weather parameters
**SPC Compliance**: ✅ Complete for canonical severe weather parameters
**Test Coverage**: 21 comprehensive unit tests (100% pass rate)
**Documentation**: Complete with operational guidance

## 🆘 Support

1. **Documentation**: See `README.md` for full project documentation
2. **Parameter Reference**: See `DERIVED_PARAMETERS_LATEST.md` for all 108 parameters
3. **Version History**: See `DERIVED_PARAMETERS_V2.1.md` and `DERIVED_PARAMETERS_V2.2.md`
4. **GitHub Issues**: https://github.com/FahrenheitResearch/hrrr-maps/issues

## ✅ Verification Checklist

- [ ] Conda environment created and activated
- [ ] All dependencies installed successfully
- [ ] Test suite passes completely
- [ ] Can list available parameters
- [ ] Can process a simple field (sbcape)
- [ ] Can generate a map visualization
- [ ] Output directory structure is created properly

Once all items are checked, your HRRR Maps system is ready for operational use!

---

**Portable Version Created**: $(date)
**Source Repository**: https://github.com/FahrenheitResearch/hrrr-maps
**Documentation Version**: v2.2 Latest
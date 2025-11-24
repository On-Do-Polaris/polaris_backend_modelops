"""
NetCDF 파일 구조 검사 스크립트
"""
import sys
import netCDF4 as nc
import tarfile
import tempfile
import os
from pathlib import Path

if len(sys.argv) < 2:
    print("Usage: python inspect_netcdf.py <nc_file>")
    sys.exit(1)

nc_file = Path(sys.argv[1])
if not nc_file.exists():
    print(f"File not found: {nc_file}")
    sys.exit(1)

print(f"Inspecting: {nc_file.name}")
print("=" * 60)

# Check if file is a tar.gz (gzipped tar)
try:
    with tarfile.open(nc_file, 'r:gz') as tar:
        members = tar.getmembers()
        if len(members) == 0:
            print("ERROR: Tar archive is empty")
            sys.exit(1)

        print(f"Tar archive contains: {members[0].name}")

        # Extract the NetCDF file to temp directory
        tmpdir = tempfile.mkdtemp()
        tar.extract(members[0], path=tmpdir)
        extracted_file = os.path.join(tmpdir, members[0].name)

    ds = nc.Dataset(extracted_file, 'r')
except Exception as e:
    print(f"ERROR: {e}")
    # Try directly as NetCDF
    print("Trying to open as direct NetCDF...")
    ds = nc.Dataset(nc_file, 'r')

print(f"\nDimensions:")
for dim_name, dim in ds.dimensions.items():
    print(f"  {dim_name}: {len(dim)}")

print(f"\nVariables:")
for var_name, var in ds.variables.items():
    print(f"  {var_name}: {var.shape} - {var.dtype}")
    if hasattr(var, 'long_name'):
        print(f"    long_name: {var.long_name}")
    if hasattr(var, 'units'):
        print(f"    units: {var.units}")

# Sample data
if 'time' in ds.variables:
    print(f"\nTime variable:")
    time_var = ds.variables['time']
    print(f"  First 5 values: {time_var[:5]}")
    if hasattr(time_var, 'units'):
        print(f"  Units: {time_var.units}")

if 'lon' in ds.variables:
    print(f"\nLongitude:")
    print(f"  Range: {ds.variables['lon'][:].min()} to {ds.variables['lon'][:].max()}")
    print(f"  First 5: {ds.variables['lon'][:5]}")

if 'lat' in ds.variables:
    print(f"\nLatitude:")
    print(f"  Range: {ds.variables['lat'][:].min()} to {ds.variables['lat'][:].max()}")
    print(f"  First 5: {ds.variables['lat'][:5]}")

# Find data variable (usually TA, RN, etc.)
data_vars = [v for v in ds.variables.keys() if v not in ['time', 'lon', 'lat', 'x', 'y']]
if data_vars:
    print(f"\nData variables: {data_vars}")
    for dv in data_vars:
        var = ds.variables[dv]
        print(f"\n{dv}:")
        print(f"  Shape: {var.shape}")
        print(f"  Dimensions: {var.dimensions}")
        print(f"  Sample value: {var[0,0,0] if len(var.shape)==3 else var[0,0]}")

ds.close()
print("\n" + "=" * 60)

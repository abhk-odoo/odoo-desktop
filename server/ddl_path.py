import platform
import ctypes
from pathlib import Path
from typing import Optional
import usb.backend.libusb1

class LibUSBBackendLoader:
    """Handles loading of libusb backend with proper platform-specific handling."""
    
    # Platform to library name mapping
    LIBRARY_MAP = {
        'Windows': {
            '32bit': 'libusb-1.0_x32.dll',
            '64bit': 'libusb-1.0_x64.dll'
        },
        'Linux': {
            'default': 'libusb-1.0.so',
            'fallback_paths': [
                '/usr/lib/x86_64-linux-gnu/libusb-1.0.so.0',
                '/usr/lib64/libusb-1.0.so.0',
                '/usr/lib/libusb-1.0.so.0'
            ]
        },
        'Darwin': {
            'default': 'libusb-1.0.dylib',
            'fallback_paths': [
                '/usr/local/opt/libusb/lib/libusb-1.0.0.dylib',
                '/opt/homebrew/lib/libusb-1.0.dylib'
            ]
        }
    }

    def __init__(self):
        self.system = platform.system()
        self.arch, _ = platform.architecture()
        self.base_path = Path(__file__).parent
        self.libusb_path = self._get_library_path()

    def _get_library_path(self) -> Optional[Path]:
        """Determine the correct libusb library path for the current platform."""
        
        if self.system not in self.LIBRARY_MAP:
            print(f"[WARNING] Unsupported platform: {self.system}")
            return None

        platform_config = self.LIBRARY_MAP[self.system]
        
        # Windows: use architecture-specific DLL
        if self.system == 'Windows':
            dll_name = platform_config.get(self.arch)
            if dll_name:
                dll_path = self.base_path / 'libusb' / dll_name
                return dll_path if dll_path.exists() else None
        
        # Linux/macOS: check bundled library first, then system paths
        elif self.system in ['Linux', 'Darwin']:
            # Check bundled library
            bundled_path = self.base_path / 'libusb' / platform_config['default']
            if bundled_path.exists():
                return bundled_path
            
            # Fall back to system libraries
            for fallback_path in platform_config.get('fallback_paths', []):
                if Path(fallback_path).exists():
                    print(f"[INFO] Using system library: {fallback_path}")
                    return Path(fallback_path)
        
        print(f"[WARNING] No suitable libusb library found for {self.system} {self.arch}")
        return None

    def _test_library_load(self, lib_path: Path) -> bool:
        """Test if the library can be successfully loaded."""
        try:
            ctypes.CDLL(str(lib_path))
            print(f"[INFO] Successfully loaded libusb: {lib_path}")
            return True
        except (OSError, AttributeError) as e:
            print(f"[ERROR] Failed to load libusb library {lib_path}: {e}")
            return False

    def load_backend(self):
        """Load and return the libusb backend."""
        
        if self.libusb_path and self._test_library_load(self.libusb_path):
            try:
                backend = usb.backend.libusb1.get_backend(
                    find_library=lambda x: str(self.libusb_path)
                )
                if backend is not None:
                    print("[INFO] Libusb backend loaded successfully")
                    return backend
            except Exception as e:
                print(f"[ERROR] Failed to initialize libusb backend: {e}")
        
        # Fallback to system default
        print("[INFO] Falling back to system libusb backend")
        try:
            return usb.backend.libusb1.get_backend()
        except Exception as e:
            print(f"[ERROR] Failed to load system libusb backend: {e}")
            return None

    def get_backend_info(self) -> dict:
        """Get information about the loaded backend for debugging."""
        return {
            'system': self.system,
            'architecture': self.arch,
            'library_path': str(self.libusb_path) if self.libusb_path else None,
            'library_exists': self.libusb_path.exists() if self.libusb_path else False,
            'base_path': str(self.base_path)
        }


# Simplified interface functions
def load_libusb_backend():
    """Main function to load libusb backend."""
    loader = LibUSBBackendLoader()

    # Print backend information for debugging
    backend_info = loader.get_backend_info()
    print(f"[INFO] Libusb backend configuration: {backend_info}")
    
    return loader.load_backend()

from brainaccess import core
from brainaccess.utils.exceptions import BrainAccessException


def main() -> None:
    print("BrainAccess Core version:", core.get_version())

    try:
        core.init()
        devices = core.scan()
    except BrainAccessException as exc:
        print("Scan failed:", exc)
        return
    finally:
        core.close()

    if not devices:
        print("No devices found.")
        return

    print(f"Devices found: {len(devices)}")
    for dev in devices:
        print(f"- {dev.name} ({dev.mac_address})")


if __name__ == "__main__":
    main()

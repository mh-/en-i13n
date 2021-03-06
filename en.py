import click
import frida
from frida.core import Session, Device, Script


allow_script = "js/allow.js"
signature_script = "js/signature.js"
patche10_script = "js/patch_e10.js"


class FridaWrapper:
    def __init__(self, device: Device, session: Session):
        self.device = device
        self.session = session

    @staticmethod
    def attach(device: Device, app_name: str):
        session: Session = device.attach(app_name)
        return FridaWrapper(device, session)

    def readjs(self, path: str) -> Script:
        with open(path) as f:
            code = f.read()
        return self.session.create_script(code)

    def inject(self, js_file: str) -> Script:
        script: Script = self.readjs(js_file)
        script.load()
        return script


@click.group()
def main():
    pass


@main.command("list-allowed")
def list_allowed():
    """List all the app names allowed by Exposure Notifications"""
    device = frida.get_usb_device()

    gms = FridaWrapper.attach(device, "com.google.android.gms.persistent")
    gms.inject(allow_script)

    input()


@main.command("get-signature")
@click.option("-p", "--package", "package", help="Package name", required=True)
def get_signature(package):
    """Get signature of the specified app"""
    device = frida.get_usb_device()
    app = FridaWrapper.attach(device, package)
    app.inject(signature_script)

    input()


def sign(package, signature, patche10, forcedk, unlimiteddk):
    device = frida.get_usb_device()

    gms = FridaWrapper.attach(device, "com.google.android.gms.persistent")
    allow = gms.inject(allow_script)
    if patche10:
        gms.inject(patche10_script)

    payload = {
        "packageName": package,
        "signatureSha": signature,
        "forcedk": forcedk,
        "unlimiteddk": unlimiteddk
    }

    allow.post({"type": "signature", "payload": payload})

    input()


@main.command("sign")
@click.option("-p", "--package", "package", help="Package name (has to be one of the allowed apps)", required=True)
@click.option("-s", "--signature", "signature", help="SHA-256 of the app signature", required=True)
@click.option("-f", "--force-dk", "forcedk", is_flag=True, help="Force Diagnosis Keys signature validation")
@click.option("-u", "--unlimited-dk", "unlimiteddk", is_flag=True,
              help="Limit on number of calls to provideDiagnosisKeys resets every 1ms instead of 24h "
                   "(careful - going back to the previous behavior after using this option requires "
                   "cleaning all the app data)")
@click.option("-e", "--patch-e10", "patche10", is_flag=True,
              help="Patch bug in Play Services causing error 10 (Pipe is closed, affects Android 6)")
def sign_command(**kwargs):
    """Allow the custom app to use Exposure Notifications"""
    sign(**kwargs)


@main.command("patch")
def patch():
    """Patch a bug in Play Services affecting Android 6"""
    sign("dummy", "dummy", True, False, False)


if __name__ == "__main__":
    main()

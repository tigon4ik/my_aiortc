from OpenSSL import crypto
from OpenSSL.crypto import FILETYPE_PEM
from aiortc import RTCCertificate
from cryptography import x509


if __name__ == '__main__':
    with open('webinar.crt', 'rb') as cert_file:
        cert_data = cert_file.read()
        cert = crypto.load_certificate(FILETYPE_PEM, cert_data)

    rtc_cert = RTCCertificate(cert.get_pubkey(), cert)
    print(rtc_cert.getFingerprints())

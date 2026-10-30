import qrcode = require("qrcode-generator");

const RECOVERY_KEY_PATTERN = /^Q1-[0-9A-HJKMNP-TV-Z-]{50,120}$/;

export function recoveryKeyQrSvg(value: string): string {
  if (!RECOVERY_KEY_PATTERN.test(value)) {
    throw new Error("recovery key format is invalid");
  }
  const code = qrcode(0, "M");
  code.addData(value);
  code.make();
  return code.createSvgTag({
    cellSize: 4,
    margin: 4,
    scalable: true,
  });
}

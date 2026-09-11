import Image from "next/image";

/** CableGuard wordmark for dark backgrounds (design asset `Logo_black_big.png`). */
export function Logo() {
  return (
    <Image
      src="/brand/cableguard-logo.png"
      alt="CableGuard"
      width={1280}
      height={460}
      priority
      className="mx-1.5 block h-auto w-[150px]"
    />
  );
}

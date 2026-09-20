import Image from "next/image";

/**
 * CableGuard wordmark (design asset `public/Logo_white_big.svg`).
 *
 * The file is a black wordmark on an opaque white plate, so on the ink
 * backgrounds it is used on (sidebar, login) it is inverted to a white
 * wordmark and the plate is blended away with `screen`. `unoptimized` keeps
 * the SVG out of the image optimiser, which refuses SVGs by default.
 */
export function Logo() {
  return (
    <Image
      src="/Logo_white_big.svg"
      alt="CableGuard"
      width={1272}
      height={460}
      priority
      unoptimized
      className="mx-1.5 block h-auto w-[150px] invert mix-blend-screen"
    />
  );
}

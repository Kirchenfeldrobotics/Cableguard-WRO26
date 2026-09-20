import type { Metadata } from "next";

import { CompareView } from "@/features/compare/compare-view";

export const metadata: Metadata = { title: "Compare runs" };

const first = (value: string | string[] | undefined) => (Array.isArray(value) ? value[0] : value);

export default async function ComparePage(props: PageProps<"/compare">) {
  const { rope, a, b } = await props.searchParams;
  return <CompareView ropeParam={first(rope)} compared={first(a)} reference={first(b)} />;
}

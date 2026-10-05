import { ButtonLink } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/heading";
import { routes } from "@/lib/routes";

export default function NotFound() {
  return (
    <>
      <PageHeader title="Not found" />
      <ButtonLink href={routes.dashboard} size="lg" className="mt-stack max-sm:w-full sm:w-[260px]">
        Back to the dashboard
      </ButtonLink>
    </>
  );
}

import { createFileRoute } from "@tanstack/react-router";
import { Hero } from "#/components/hero";
import { VisualDemo } from "#/components/visual-demo";
import { SocialProof } from "#/components/social-proof";
import { ComparisonTable } from "#/components/comparison-table";
import { FeaturePillars } from "#/components/feature-pillars";
import { DeploymentCards } from "#/components/deployment-cards";
import { RouterSection } from "#/components/router-section";
import { ProviderShowcase } from "#/components/provider-showcase";
import { InteractiveDemo } from "#/components/interactive-demo";
import { CtaBottom } from "#/components/cta-bottom";

export const Route = createFileRoute("/")({ component: Landing });

function Landing() {
	return (
		<>
			<Hero />
			<VisualDemo />
			<SocialProof />
			<ComparisonTable />
			<FeaturePillars />
			<DeploymentCards />
			<RouterSection />
			<ProviderShowcase />
			<InteractiveDemo />
			<CtaBottom />
		</>
	);
}

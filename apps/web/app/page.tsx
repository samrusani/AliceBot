import { HomePageContent } from "../components/home-page-content";
import { legacySurfacesEnabled } from "../lib/legacy-surfaces.server";

export default function HomePage() {
  return <HomePageContent legacyEnabled={legacySurfacesEnabled()} />;
}

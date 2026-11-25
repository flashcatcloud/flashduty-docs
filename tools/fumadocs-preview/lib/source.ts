import { defineDocs } from "fumadocs-mdx/macro";
import { loader } from "fumadocs-core/source";
import pages from "@/generated/pages.json";

const docs = defineDocs({ dir: "content" });
export const source = loader({ baseUrl: "/", source: docs.toFumadocsSource() });
export { pages };

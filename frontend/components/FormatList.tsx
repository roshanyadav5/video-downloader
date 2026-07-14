import type { VideoFormat } from "@/lib/types";
import FormatRow from "./FormatRow";

export default function FormatList({ url, formats }: { url: string; formats: VideoFormat[] }) {
  if (formats.length === 0) {
    return (
      <p className="px-5 py-6 text-center text-sm text-muted sm:px-6">
        No downloadable formats were found for this video.
      </p>
    );
  }

  return (
    <div className="space-y-2 px-5 pb-5 sm:px-6 sm:pb-6">
      {formats.map((format) => (
        <FormatRow key={format.format_id} url={url} format={format} />
      ))}
    </div>
  );
}

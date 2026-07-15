export default function AmbientBackground() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden" aria-hidden="true">
      <div className="absolute -left-32 -top-32 h-96 w-96 animate-pulse-slow rounded-full bg-primary/20 blur-[100px]" />
      <div className="absolute -right-24 top-1/3 h-80 w-80 animate-pulse-slow rounded-full bg-success/10 blur-[100px] [animation-delay:2s]" />
      <div className="absolute bottom-0 left-1/3 h-72 w-72 animate-pulse-slow rounded-full bg-primary-soft/15 blur-[100px] [animation-delay:4s]" />
    </div>
  );
}

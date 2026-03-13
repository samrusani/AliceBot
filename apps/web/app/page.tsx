const milestones = [
  "API foundation and migrations",
  "Continuity event store",
  "Web dashboard shell",
  "Worker orchestration",
];

export default function HomePage() {
  return (
    <main
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        background:
          "radial-gradient(circle at top, rgba(245, 196, 122, 0.35), transparent 45%), #f4efe6",
        color: "#1f2933",
        padding: "2rem",
        fontFamily: "Georgia, 'Times New Roman', serif",
      }}
    >
      <section
        style={{
          width: "min(720px, 100%)",
          border: "1px solid rgba(31, 41, 51, 0.12)",
          borderRadius: "24px",
          padding: "2rem",
          background: "rgba(255, 255, 255, 0.82)",
          boxShadow: "0 20px 60px rgba(31, 41, 51, 0.08)",
        }}
      >
        <p style={{ letterSpacing: "0.18em", textTransform: "uppercase" }}>
          AliceBot Foundation
        </p>
        <h1 style={{ fontSize: "clamp(2.5rem, 6vw, 4rem)", margin: "0.5rem 0 1rem" }}>
          Operational shell for the modular monolith
        </h1>
        <p style={{ fontSize: "1.1rem", lineHeight: 1.7 }}>
          The web app is intentionally minimal in this sprint. It exists to prove repository
          structure while continuity, migrations, and safety primitives land in the API layer.
        </p>
        <ul style={{ margin: "1.5rem 0 0", paddingLeft: "1.25rem", lineHeight: 1.8 }}>
          {milestones.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>
    </main>
  );
}


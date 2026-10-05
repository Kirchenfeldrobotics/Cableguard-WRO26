import { jsPDF } from "jspdf";

import { api } from "@/lib/api/client";
import type { DefectKind, Rope, Run } from "@/lib/api/types";
import type { Finding } from "@/lib/defects";
import {
  defectClassLabel,
  defectTypeLabel,
  formatCamera,
  formatConfidence,
  formatDateTime,
  formatMetres,
  formatRunDuration,
  formatSpan,
  shortId,
} from "@/lib/format";

/** A4 portrait, in millimetres. */
const PAGE = { w: 210, h: 297, margin: 16 };
const WIDTH = PAGE.w - 2 * PAGE.margin;
/** Lowest a block may reach, the footer sits below it. */
const FLOOR = PAGE.h - 20;

/** The tokens of app/globals.css. A PDF cannot read them off the stylesheet. */
const INK = "#0a0a0a";
const MUTED = "#4a4a4a";
const SUBTLE = "#6e6e6e";
const SURFACE = "#f2f2f2";
const RULE = "#e2e2e2";
const KIND_COLOR: Record<DefectKind, string> = { lf: "#c11119", lma: "#e8a33d" };

const FACT = { w: (WIDTH - 3 * 4) / 4, h: 15, gap: 4 };
const ROW_H = 7;
const PHOTO = { w: (WIDTH - 6) / 2, gap: 6, caption: 11 };

/** Where each column of the findings table starts, or ends when it is right-aligned. */
const COLUMNS = [
  { title: "#", x: 0 },
  { title: "Position", x: 8 },
  { title: "Flaw", x: 42 },
  { title: "Type", x: 80 },
  { title: "Confidence", x: 134, right: true },
  { title: "Detections", x: 154, right: true },
  { title: "Status", x: 159 },
];

/** Frames are fetched a few at a time, a long run has dozens of findings. */
const FETCH_AT_ONCE = 4;

interface Style {
  size: number;
  weight: "normal" | "bold";
  color: string;
}

const TITLE: Style = { size: 22, weight: "bold", color: INK };
const HEADING: Style = { size: 12, weight: "bold", color: INK };
const VALUE: Style = { size: 11, weight: "bold", color: INK };
const BODY: Style = { size: 8.5, weight: "normal", color: INK };
const STRONG: Style = { size: 8.5, weight: "bold", color: INK };
const NOTE: Style = { size: 7.5, weight: "normal", color: SUBTLE };
const META: Style = { size: 10, weight: "normal", color: MUTED };

export interface RunReportInput {
  rope: Rope;
  run: Run;
  /** Sorted by position, as the run page lists them. */
  findings: Finding[];
  /** Rows the robot stored for the run. */
  detectionCount: number;
  /** JPEG of the frame a finding's clearest detection was made in, by the id of that detection. */
  photos: Map<string, Uint8Array>;
  exportedAt: Date;
}

/**
 * The built-in PDF fonts only know Latin-1. The dash the app shows for a missing value is
 * outside it, and a rope name may be too.
 */
function plain(text: string): string {
  return text.replace(/—/g, "-").replace(/[^ -ÿ]/g, "?");
}

function reviewLabel(finding: Finding): string {
  return finding.reviewed ? "Reviewed" : "Unreviewed";
}

/** Lays the report out. Nothing in here touches the browser, so it runs the same anywhere. */
export function buildRunReport({
  rope,
  run,
  findings,
  detectionCount,
  photos,
  exportedAt,
}: RunReportInput): jsPDF {
  const doc = new jsPDF({ unit: "mm", format: "a4", compress: true });
  const left = PAGE.margin;
  const reviewed = findings.filter((f) => f.reviewed).length;
  let y = PAGE.margin;

  doc.setProperties({ title: plain(`Run report ${rope.name} ${shortId(run.id)}`), creator: "CableGuard" });

  const write = (text: string, x: number, at: number, style: Style, align: "left" | "right" = "left") => {
    doc.setFont("helvetica", style.weight);
    doc.setFontSize(style.size);
    doc.setTextColor(style.color);
    doc.text(plain(text), x, at, { align });
  };

  /** Moves on to a new page when the next block would run into the footer. */
  const room = (height: number) => {
    if (y + height <= FLOOR) return false;
    doc.addPage();
    y = PAGE.margin;
    return true;
  };

  const heading = (text: string) => {
    y += 6;
    room(20);
    write(text.toUpperCase(), left, y + 4, HEADING);
    y += 9;
  };

  write("Run report", left, y + 7, TITLE);
  write(`${rope.name} · ${shortId(run.id)}`, left, y + 14, META);
  y += 21;

  const facts = [
    ["Started", formatDateTime(run.started_at)],
    ["Duration", formatRunDuration(run)],
    ["Rope length", formatMetres(rope.length_m)],
    ["Exported", formatDateTime(exportedAt.toISOString())],
    ["Findings", String(findings.length)],
    ["Reviewed", String(reviewed)],
    ["Unreviewed", String(findings.length - reviewed)],
    ["Detections", String(detectionCount)],
  ];
  facts.forEach(([label, value], i) => {
    const x = left + (i % 4) * (FACT.w + FACT.gap);
    const top = y + Math.floor(i / 4) * (FACT.h + FACT.gap);
    doc.setFillColor(SURFACE);
    doc.roundedRect(x, top, FACT.w, FACT.h, 2, 2, "F");
    write(value, x + 3.5, top + 6.5, VALUE);
    write(label, x + 3.5, top + 11.5, NOTE);
  });
  y += 2 * FACT.h + FACT.gap;

  if (rope.length_m) {
    const length = rope.length_m;
    const at = (m: number) => (Math.max(0, Math.min(length, m)) / length) * WIDTH;

    heading("Rope");
    write("0", left, y + 2, NOTE);
    write(formatMetres(length), left + WIDTH, y + 2, NOTE, "right");
    doc.setFillColor(SURFACE);
    doc.roundedRect(left, y + 4, WIDTH, 7, 1.5, 1.5, "F");
    for (const finding of findings) {
      // A finding covers the stretch of its detections, down to a width that still shows.
      const width = Math.max(at(finding.to) - at(finding.from), 0.7);
      const centre = (at(finding.from) + at(finding.to)) / 2;
      doc.setFillColor(KIND_COLOR[finding.kind]);
      doc.rect(left + centre - width / 2, y + 4.8, width, 5.4, "F");
    }
    y += 15;

    let x = left;
    for (const kind of ["lf", "lma"] as const) {
      const label = `${defectTypeLabel(kind)} (${kind.toUpperCase()})`;
      doc.setFillColor(KIND_COLOR[kind]);
      doc.rect(x, y - 2.4, 1.2, 3, "F");
      write(label, x + 2.6, y, NOTE);
      x += doc.getTextWidth(plain(label)) + 9;
    }
    y += 2;
  }

  const tableHead = () => {
    for (const column of COLUMNS) {
      write(column.title, left + column.x, y + 4, NOTE, column.right ? "right" : "left");
    }
    doc.setDrawColor(RULE);
    doc.setLineWidth(0.3);
    doc.line(left, y + 6, left + WIDTH, y + 6);
    y += ROW_H;
  };

  heading("Findings");
  if (findings.length === 0) {
    write("No findings.", left, y + 4, META);
    y += ROW_H;
  } else {
    tableHead();
    findings.forEach((finding, i) => {
      if (room(ROW_H)) tableHead();
      const cells = [
        String(i + 1),
        formatSpan(finding.from, finding.to),
        defectClassLabel(finding.best.label),
        defectTypeLabel(finding.kind),
        formatConfidence(finding.confidence),
        String(finding.detections.length),
        reviewLabel(finding),
      ];
      cells.forEach((cell, c) => {
        const column = COLUMNS[c];
        write(cell, left + column.x, y + 4.4, c === 1 ? STRONG : BODY, column.right ? "right" : "left");
      });
      doc.setDrawColor(RULE);
      doc.setLineWidth(0.15);
      doc.line(left, y + ROW_H - 0.4, left + WIDTH, y + ROW_H - 0.4);
      y += ROW_H;
    });
  }

  // One photo per finding: the frame of its clearest detection, numbered as in the table.
  const tiles = findings.flatMap((finding, i) => {
    const jpeg = photos.get(finding.best.id);
    if (!jpeg) return [];
    const { width, height } = doc.getImageProperties(jpeg);
    return [{ finding, number: i + 1, jpeg, height: (PHOTO.w * height) / width }];
  });

  if (tiles.length > 0) heading("Photos");
  for (let i = 0; i < tiles.length; i += 2) {
    const row = tiles.slice(i, i + 2);
    const height = Math.max(...row.map((tile) => tile.height)) + PHOTO.caption;
    room(height);

    row.forEach(({ finding, number, jpeg, height: tall }, column) => {
      const x = left + column * (PHOTO.w + PHOTO.gap);
      const { best } = finding;
      doc.addImage(jpeg, "JPEG", x, y, PHOTO.w, tall);

      const { box_x1: x1, box_y1: y1, box_x2: x2, box_y2: y2 } = best;
      if (x1 !== null && y1 !== null && x2 !== null && y2 !== null) {
        doc.setDrawColor(KIND_COLOR[finding.kind]);
        doc.setLineWidth(0.6);
        doc.rect(x + x1 * PHOTO.w, y + y1 * tall, (x2 - x1) * PHOTO.w, (y2 - y1) * tall);
      }

      write(
        `${number} · ${formatMetres(best.pos_to_start)} · ${defectClassLabel(best.label)} · ${formatConfidence(best.confidence)}`,
        x,
        y + tall + 4.5,
        STRONG,
      );
      write(
        `${formatCamera(best.cam)} · ${formatDateTime(best.created_at)} · ${reviewLabel(finding)}`,
        x,
        y + tall + 8.5,
        NOTE,
      );
    });
    y += height + 5;
  }

  const pages = doc.getNumberOfPages();
  for (let page = 1; page <= pages; page++) {
    doc.setPage(page);
    write(`CableGuard · ${rope.name} · ${shortId(run.id)}`, left, PAGE.h - 10, NOTE);
    write(`Page ${page} of ${pages}`, left + WIDTH, PAGE.h - 10, NOTE, "right");
  }

  return doc;
}

function fileName(rope: Rope, run: Run): string {
  // Accents are split off their letter and dropped first, so `Säntis` is `santis`, not `s-ntis`.
  const plainName = rope.name.normalize("NFKD").replace(/[̀-ͯ]/g, "");
  const slug = plainName.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
  return `cableguard-${slug || "rope"}-${shortId(run.id).toLowerCase()}.pdf`;
}

/** Collects the photos, builds the report and hands it to the browser as a download. */
export async function downloadRunReport(input: Omit<RunReportInput, "photos" | "exportedAt">): Promise<void> {
  const photos = new Map<string, Uint8Array>();
  const stored = input.findings.map((f) => f.best).filter((defect) => defect.frame_id !== null);

  for (let i = 0; i < stored.length; i += FETCH_AT_ONCE) {
    await Promise.all(
      stored.slice(i, i + FETCH_AT_ONCE).map(async (defect) => {
        const frame = await api.defects.frame(defect.id);
        photos.set(defect.id, new Uint8Array(await frame.arrayBuffer()));
      }),
    );
  }

  buildRunReport({ ...input, photos, exportedAt: new Date() }).save(fileName(input.rope, input.run));
}

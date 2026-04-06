"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Search } from "lucide-react";

import { HelpHint } from "@/components/help-hint";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { PLATFORM_CAPABILITIES } from "@/lib/platform-capabilities";

export default function PlatformPage() {
  const [q, setQ] = useState("");
  const [track, setTrack] = useState<string | "all">("all");

  const tracks = useMemo(() => {
    const s = new Set<string>();
    for (const c of PLATFORM_CAPABILITIES) s.add(c.track);
    return Array.from(s).sort();
  }, []);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return PLATFORM_CAPABILITIES.filter((c) => {
      if (track !== "all" && c.track !== track) return false;
      if (!needle) return true;
      const hay = `${c.name} ${c.track} ${c.description}`.toLowerCase();
      return hay.includes(needle);
    });
  }, [q, track]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight flex items-center gap-2">
            Platform map
            <HelpHint helpId="platform-hub" label="Platform capabilities" />
          </h2>
          <p className="text-muted-foreground mt-1 text-sm max-w-2xl">
            Everything the backend exposes or documents, with honest status. Research and Polymarket routes have read-only explorer pages under{" "}
            <code className="text-xs">/platform/…</code>.
          </p>
        </div>
        <Button variant="outline" size="sm" asChild>
          <Link href="/start">Getting started</Link>
        </Button>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Filters</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              className="pl-9"
              placeholder="Search capabilities…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              aria-label="Search capabilities"
            />
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              size="sm"
              variant={track === "all" ? "default" : "outline"}
              onClick={() => setTrack("all")}
            >
              All tracks
            </Button>
            {tracks.map((t) => (
              <Button
                key={t}
                type="button"
                size="sm"
                variant={track === t ? "default" : "outline"}
                onClick={() => setTrack(t)}
              >
                {t}
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Desktop table */}
      <div className="hidden rounded-md border md:block">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Capability</TableHead>
              <TableHead>Track</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="min-w-[240px]">Description</TableHead>
              <TableHead className="text-right">Open</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((c) => (
              <TableRow key={c.id}>
                <TableCell className="font-medium">{c.name}</TableCell>
                <TableCell className="text-muted-foreground">{c.track}</TableCell>
                <TableCell>
                  <StatusBadge status={c.status} />
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {c.description}
                </TableCell>
                <TableCell className="text-right">
                  {c.href ? (
                    <Button variant="link" className="h-auto p-0" asChild>
                      <Link href={c.href}>Open</Link>
                    </Button>
                  ) : (
                    <span className="text-xs text-muted-foreground">—</span>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Mobile cards */}
      <ul className="space-y-3 md:hidden">
        {filtered.map((c) => (
          <li key={c.id}>
            <Card>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between gap-2">
                  <CardTitle className="text-base">{c.name}</CardTitle>
                  <StatusBadge status={c.status} />
                </div>
                <p className="text-xs text-muted-foreground">{c.track}</p>
              </CardHeader>
              <CardContent className="space-y-2 text-sm text-muted-foreground">
                <p>{c.description}</p>
                {c.href ? (
                  <Button variant="secondary" size="sm" asChild>
                    <Link href={c.href}>Open</Link>
                  </Button>
                ) : null}
              </CardContent>
            </Card>
          </li>
        ))}
      </ul>

      {filtered.length === 0 ? (
        <p className="text-center text-sm text-muted-foreground py-8">
          No matches. Clear filters or search.
        </p>
      ) : null}
    </div>
  );
}

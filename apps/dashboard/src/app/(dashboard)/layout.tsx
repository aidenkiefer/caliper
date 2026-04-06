import { DashboardFrame } from "@/components/dashboard-frame";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <DashboardFrame>{children}</DashboardFrame>;
}

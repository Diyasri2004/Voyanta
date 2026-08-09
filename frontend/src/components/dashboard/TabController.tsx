"use client";

import CommandCenter, { PILLARS } from "./CommandCenter";

export { PILLARS };

export default function TabController(props: any) {
  return <CommandCenter {...props} />;
}

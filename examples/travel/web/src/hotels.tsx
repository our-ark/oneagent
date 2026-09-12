import React from "react";
import { createRoot } from "react-dom/client";
import { TravelApp } from "./TravelApp";
createRoot(document.getElementById("root")!).render(
  <TravelApp site="hotels" />,
);

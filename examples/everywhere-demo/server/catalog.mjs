export const catalogs = {
  dayform: [
    {
      id: "day-one",
      app: "dayform",
      name: "Day One",
      color: "Ink",
      price: 98,
      shipping: 0,
      taxRate: 0.1,
      fit: "Roomy toe box",
      cushioning: "Soft foam footbed",
      arrival: "Thursday",
      sizes: [8, 9, 10, 11],
      image: "/products/dayform.jpg",
      description:
        "A little room to move. A softer landing. Your everyday, made easier.",
    },
  ],
  stride: [
    {
      id: "arc-02",
      app: "stride",
      name: "Arc 02",
      color: "Graphite",
      price: 112,
      shipping: 0,
      taxRate: 0.1,
      fit: "Slim, structured fit",
      cushioning: "Responsive, firmer cushioning",
      arrival: "Friday",
      sizes: [8, 9, 10, 11],
      image: "/products/stride.jpg",
      description: "Technical mesh. Sculpted support. Engineered for the city.",
    },
  ],
};
export const products = Object.values(catalogs).flat();
export const productFor = (app, id) => catalogs[app]?.find((p) => p.id === id);
export const totalFor = (p) =>
  Math.round((p.price + p.shipping + p.price * p.taxRate) * 100) / 100;
export const appNames = {
  phone: "Companion",
  dayform: "DAYFORM",
  stride: "STRIDE / STUDIO",
  desktop: "Desktop",
};

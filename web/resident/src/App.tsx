import { useState } from "react";
import ActivationScreen from "./screens/ActivationScreen";
import QRScreen from "./screens/QRScreen";

function App() {
  const [isActivated, setIsActivated] = useState(() => {
    return !!localStorage.getItem("resident_id");
  });

  if (!isActivated) {
    return <ActivationScreen onActivated={() => setIsActivated(true)} />;
  }

  return <QRScreen />;
}

export default App;

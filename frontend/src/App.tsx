import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Toaster } from 'sonner';
import { useEffect } from 'react';
import { useThemeStore } from './store/themeStore';
import { Layout } from './components/layout/Layout';
import { Home } from './pages/public/Home';
import { EventDetails } from './pages/public/EventDetails';
import { Login } from './pages/public/Login';
import { Register } from './pages/public/Register';
import { Checkout } from './pages/client/Checkout';
import { CheckoutSuccess } from './pages/client/CheckoutSuccess';
import { CheckoutCancel } from './pages/client/CheckoutCancel';
import { MyTickets } from './pages/client/MyTickets';
import { OrganizerDashboard } from './pages/organizer/OrganizerDashboard';
import { GatekeeperScan } from './pages/gatekeeper/GatekeeperScan';

function App() {
  const { theme } = useThemeStore();

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  return (
    <BrowserRouter>
      <Toaster theme={theme} position="top-right" richColors />
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/events/:id" element={<EventDetails />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/checkout/success" element={<CheckoutSuccess />} />
          <Route path="/checkout/cancel" element={<CheckoutCancel />} />
          <Route path="/checkout/:id" element={<Checkout />} />
          <Route path="/tickets" element={<MyTickets />} />
          <Route path="/organizer" element={<OrganizerDashboard />} />
          <Route path="/gatekeeper" element={<GatekeeperScan />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;

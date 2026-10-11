import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom';
import BrandBar from './components/BrandBar';
import Header from './components/Header';
import { useAttendeePath } from './hooks/useAttendeePath';
import HostPage from './pages/HostPage';
import LandingPage from './pages/LandingPage';
import LeaderboardPage from './pages/LeaderboardPage';
import MarketsPage from './pages/MarketsPage';
import ReportsPage from './pages/ReportsPage';
import SetupPage from './pages/SetupPage';
import SignUpPage from './pages/SignUpPage';

export default function App() {
  return (
    <Routes>
      {/* For hosts. */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/setup/*" element={<SetupPage />} />
      <Route path="/host" element={<HostLayout />} />

      {/* For attendees. The slug names the event in the link; it is not used to fetch anything. */}
      <Route path="/e/:slug" element={<AttendeeLayout />}>
        <Route index element={<MarketsPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="reports/:teamId" element={<ReportsPage />} />
        <Route path="leaderboard" element={<LeaderboardPage />} />
        <Route path="signup" element={<SignUpPage />} />
      </Route>

      {/* Where the attendee pages lived before they moved under /e/:slug. */}
      <Route path="/reports/*" element={<MovedToAttendeeApp />} />
      <Route path="/leaderboard" element={<MovedToAttendeeApp />} />
      <Route path="/signup" element={<MovedToAttendeeApp />} />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function AttendeeLayout() {
  return (
    <>
      <Header />
      <Outlet />
    </>
  );
}

function HostLayout() {
  return (
    <>
      <BrandBar />
      <HostPage />
    </>
  );
}

function MovedToAttendeeApp() {
  const path = useAttendeePath();
  const { pathname, search } = useLocation();
  return <Navigate to={path(pathname) + search} replace />;
}

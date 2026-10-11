import { Navigate, Route, Routes } from 'react-router-dom';
import Header from './components/Header';
import HostPage from './pages/HostPage';
import LeaderboardPage from './pages/LeaderboardPage';
import MarketsPage from './pages/MarketsPage';
import ReportsPage from './pages/ReportsPage';
import SignUpPage from './pages/SignUpPage';

export default function App() {
  return (
    <>
      <Header />
      <Routes>
        <Route path="/" element={<MarketsPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/reports/:teamId" element={<ReportsPage />} />
        <Route path="/leaderboard" element={<LeaderboardPage />} />
        <Route path="/signup" element={<SignUpPage />} />
        {/* Not linked from the tabs: the host opens it directly. */}
        <Route path="/host" element={<HostPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}

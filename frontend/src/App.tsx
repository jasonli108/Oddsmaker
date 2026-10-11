import { Link, Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom';
import BrandBar from './components/BrandBar';
import Header from './components/Header';
import { useAttendeePath } from './hooks/useAttendeePath';
import { useEvent } from './hooks/useEvent';
import HostPage from './pages/HostPage';
import LandingPage from './pages/LandingPage';
import LeaderboardPage from './pages/LeaderboardPage';
import MarketsPage from './pages/MarketsPage';
import ReportsPage from './pages/ReportsPage';
import SignUpPage from './pages/SignUpPage';
import SummaryPage from './pages/SummaryPage';
import SetupLayout from './pages/setup/SetupLayout';
import SetupLinkPage from './pages/setup/SetupLinkPage';
import SetupLivePage from './pages/setup/SetupLivePage';
import SetupReviewPage from './pages/setup/SetupReviewPage';

export default function App() {
  return (
    <Routes>
      {/* For hosts. */}
      <Route path="/" element={<LandingPage />} />
      <Route path="/setup" element={<SetupLayout />}>
        <Route index element={<SetupLinkPage />} />
        <Route path="review" element={<SetupReviewPage />} />
        <Route path="live/:slug" element={<SetupLivePage />} />
      </Route>
      <Route path="/host/:slug" element={<HostLayout />} />
      <Route path="/host" element={<FirstEventHostPage />} />

      {/* For attendees. The slug says which event: each has its own markets, teams and players. */}
      <Route path="/e/:slug" element={<AttendeeLayout />}>
        <Route index element={<MarketsPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="reports/:teamId" element={<ReportsPage />} />
        <Route path="leaderboard" element={<LeaderboardPage />} />
        <Route path="signup" element={<SignUpPage />} />
        <Route path="summary" element={<SummaryPage />} />
        <Route path="summary/:userId" element={<SummaryPage />} />
      </Route>

      {/* Where the attendee pages lived before they moved under /e/:slug. */}
      <Route path="/reports/*" element={<MovedToAttendeeApp />} />
      <Route path="/leaderboard" element={<MovedToAttendeeApp />} />
      <Route path="/signup" element={<MovedToAttendeeApp />} />
      <Route path="/summary/*" element={<MovedToAttendeeApp />} />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function AttendeeLayout() {
  const { notFound } = useEvent();
  if (notFound) return <EventNotFound />;
  return (
    <>
      <Header />
      <Outlet />
    </>
  );
}

/** For a link to an event that was never launched here, e.g. a mistyped address. */
function EventNotFound() {
  return (
    <>
      <BrandBar />
      <div className="container stack" style={{ paddingTop: 40, maxWidth: 560, alignItems: 'flex-start' }}>
        <h1>We can't find that event</h1>
        <div className="dim">Check the link you were given, or ask the organiser to share it again.</div>
        <Link className="btn" to="/" style={{ display: 'grid', placeItems: 'center' }}>
          Go to Oddsmaker
        </Link>
      </div>
    </>
  );
}

/** /host without an event in the address: the first event's host page, or home if there is none. */
function FirstEventHostPage() {
  const { ready, slug } = useEvent();
  if (!ready) return null;
  return <Navigate to={slug ? `/host/${slug}` : '/'} replace />;
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
  const { ready } = useEvent();
  const { pathname, search } = useLocation();
  if (!ready) return null;
  return <Navigate to={path(pathname) + search} replace />;
}

import { useNavigate, useParams } from 'react-router-dom';
import { useEffect } from 'react';

/**
 * /support/:id — redirect to the Ticket Center with the drawer open.
 * The drawer in SupportListPage is the canonical detail view; this
 * route exists only so direct links and breadcrumb navigation work.
 */
export default function SupportDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  useEffect(() => {
    // Replace history entry so Back navigates out of /support entirely
    navigate(`/support?ticket=${id}`, { replace: true });
  }, [id, navigate]);

  return null;
}

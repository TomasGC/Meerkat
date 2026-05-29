import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

interface UserButtonProps {
  userId: string;
  onClick?: () => void;
  disabled?: boolean;
}

export default function UserButton({ userId, onClick, disabled = false }: UserButtonProps) {
  const [loading, setLoading] = useState(false);
  const [user, setUser] = useState<any>(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchUser(userId);
  }, [userId]);

  const fetchUser = async (id: string) => {
    setLoading(true);
    try {
      const response = await fetch(`/api/users/${id}`);
      const data = await response.json();
      setUser(data);
    } catch (error) {
      console.error('Failed to fetch user', error);
    } finally {
      setLoading(false);
    }
  };

  const handleClick = () => {
    if (onClick) {
      onClick();
    }
    navigate(`/users/${userId}`);
  };

  return (
    <button
      onClick={handleClick}
      disabled={disabled || loading}
      className="user-button"
    >
      {loading ? 'Loading...' : user?.name || 'Unknown User'}
    </button>
  );
}

export const UserList = () => {
  const [users, setUsers] = useState([]);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    const response = await fetch('/api/users');
    const data = await response.json();
    setUsers(data);
  };

  return (
    <div>
      {users.map((user: any) => (
        <UserButton key={user.id} userId={user.id} />
      ))}
    </div>
  );
};

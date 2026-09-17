interface UserButtonProps {
  userId: string;
  label?: string;
}

export function UserButton({ userId, label }: UserButtonProps) {
  return (
    <button data-user={userId}>{label ?? userId}</button>
  );
}

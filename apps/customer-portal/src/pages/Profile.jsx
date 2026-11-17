import {
  UserRound,
  Mail,
  Phone,
  ShieldCheck
} from 'lucide-react'

export default function Profile() {
  return (
    <div className="page-content profile-page">
      <div className="page-heading">
        <p className="hero-eyebrow">ACCOUNT SETTINGS</p>
        <h1>My Profile</h1>
        <p>View and manage your account information.</p>
      </div>

      <section className="profile-card">
        <UserRound className="profile-user-icon" size={48} />

        <h2>Customer Name</h2>
        <p className="profile-customer-name">WEZA Customer</p>

        <div className="profile-detail">
          <Mail size={24} />
          <span>Email Address</span>
          <strong>customer@example.com</strong>
        </div>

        <div className="profile-detail">
          <Phone size={24} />
          <span>Phone Number</span>
          <strong>07XXXXXXXX</strong>
        </div>

        <div className="profile-detail">
          <ShieldCheck size={24} />
          <span>Account Status</span>
          <strong>Active</strong>
        </div>
      </section>
    </div>
  )
}

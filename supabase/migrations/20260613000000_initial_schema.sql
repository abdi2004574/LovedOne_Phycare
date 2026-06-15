-- Drop existing objects in dependency order
drop view if exists public.appointment_summary;
drop view if exists public.patient_summary;
drop view if exists public.doctor_summary;
drop function if exists public.can_access_conversation(uuid);
drop function if exists public.is_doctor_of_patient(uuid);
drop function if exists public.get_user_role();
drop table if exists public.api_keys;
drop table if exists public.messages;
drop table if exists public.appointments;
drop table if exists public.conversations;
drop table if exists public.doctors;
drop table if exists public.patients;
drop table if exists public.profiles;
drop trigger if exists on_auth_user_created on auth.users;
drop function if exists public.handle_new_user();
drop function if exists public.handle_updated_at();

-- ============================================================
-- LovedOne PsychCare — Supabase Database Schema
-- ============================================================
-- Generated: 2026-06-13
-- Tables: profiles, patients, doctors, conversations,
--         messages, appointments, api_keys
-- Features: Foreign keys, indexes, RLS, Realtime
-- ============================================================

-- ----------------------------------------
-- Enable required extensions
-- ----------------------------------------
create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";
create extension if not exists "pg_trgm";

-- ----------------------------------------
-- Helper: updated_at trigger function
-- ----------------------------------------
create or replace function public.handle_updated_at()
returns trigger as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$ language plpgsql;

-- ----------------------------------------
-- Table: profiles
-- Extends auth.users with role-specific data.
-- ----------------------------------------
create table public.profiles (
  id uuid references auth.users on delete cascade not null primary key,
  email text unique not null,
  full_name text not null,
  phone text,
  role text not null check (role in ('patient', 'doctor', 'admin')),
  language text not null default 'en' check (language in ('en', 'ur')),
  avatar_url text,
  is_active boolean not null default true,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

comment on table public.profiles is 'User profile extending auth.users. One row per registered user.';

create index idx_profiles_email on public.profiles using btree (email);
create index idx_profiles_role on public.profiles using btree (role);
create index idx_profiles_language on public.profiles using btree (language);

create trigger set_profiles_updated_at
  before update on public.profiles
  for each row execute procedure public.handle_updated_at();

alter table public.profiles enable row level security;

-- RLS: profiles
create policy "Users can view their own profile"
  on public.profiles for select
  using (auth.uid() = id);

create policy "Users can update their own profile"
  on public.profiles for update
  using (auth.uid() = id)
  with check (auth.uid() = id);

create policy "Admins can view all profiles"
  on public.profiles for select
  using (
    exists (
      select 1 from public.profiles
      where id = auth.uid() and role = 'admin'
    )
  );

create policy "Admins can update all profiles"
  on public.profiles for update
  using (
    exists (
      select 1 from public.profiles
      where id = auth.uid() and role = 'admin'
    )
  );

create policy "Service role has full access"
  on public.profiles for all
  using (auth.role() = 'service_role');

-- ----------------------------------------
-- Table: patients
-- Extended profile for patient role users.
-- ----------------------------------------
create table public.patients (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references public.profiles(id) on delete cascade unique,
  age int check (age > 0 and age < 150),
  gender text check (gender in ('male', 'female', 'other', 'prefer_not_to_say')),
  medical_history jsonb default '{}'::jsonb,
  assigned_doctor_id uuid,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

comment on table public.patients is 'Extended patient data linked to a user profile.';

create index idx_patients_user_id on public.patients using btree (user_id);
create index idx_patients_assigned_doctor on public.patients using btree (assigned_doctor_id);
create index idx_patients_gender on public.patients using btree (gender);

create trigger set_patients_updated_at
  before update on public.patients
  for each row execute procedure public.handle_updated_at();

alter table public.patients enable row level security;

-- RLS: patients
create policy "Patients can view their own record"
  on public.patients for select
  using (
    user_id = auth.uid()
    or
    exists (
      select 1 from public.profiles
      where id = auth.uid() and role in ('admin', 'doctor')
    )
  );

create policy "Patients can insert their own record"
  on public.patients for insert
  with check (user_id = auth.uid());

create policy "Patients can update their own record"
  on public.patients for update
  using (
    user_id = auth.uid()
    or
    exists (
      select 1 from public.profiles
      where id = auth.uid() and role in ('admin', 'doctor')
    )
  )
  with check (
    user_id = auth.uid()
    or
    exists (
      select 1 from public.profiles
      where id = auth.uid() and role in ('admin', 'doctor')
    )
  );

create policy "Service role has full access"
  on public.patients for all
  using (auth.role() = 'service_role');

-- ----------------------------------------
-- Table: doctors
-- Extended profile for doctor role users.
-- ----------------------------------------
create table public.doctors (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references public.profiles(id) on delete cascade unique,
  pmdc_number text not null unique,
  specialization text not null,
  bio text,
  is_verified boolean not null default false,
  is_available boolean not null default true,
  rating numeric(3,2) not null default 0.00 check (rating >= 0 and rating <= 5),
  total_reviews int not null default 0,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

comment on table public.doctors is 'Extended doctor data including PMDC number, specialization, and ratings.';

create index idx_doctors_user_id on public.doctors using btree (user_id);
create index idx_doctors_pmdc_number on public.doctors using btree (pmdc_number);
create index idx_doctors_specialization on public.doctors using btree (specialization);
create index idx_doctors_is_available on public.doctors using btree (is_available);
create index idx_doctors_rating on public.doctors using btree (rating desc);

create trigger set_doctors_updated_at
  before update on public.doctors
  for each row execute procedure public.handle_updated_at();

alter table public.doctors enable row level security;

-- RLS: doctors
create policy "Doctors can view their own record"
  on public.doctors for select
  using (
    user_id = auth.uid()
    or
    exists (
      select 1 from public.profiles
      where id = auth.uid() and role = 'admin'
    )
  );

create policy "Patients can view verified available doctors"
  on public.doctors for select
  using (
    is_verified = true
    and is_available = true
    and
    exists (
      select 1 from public.profiles
      where id = auth.uid() and role = 'patient'
    )
  );

create policy "Doctors can update their own record"
  on public.doctors for update
  using (
    user_id = auth.uid()
    or
    exists (
      select 1 from public.profiles
      where id = auth.uid() and role = 'admin'
    )
  )
  with check (
    user_id = auth.uid()
    or
    exists (
      select 1 from public.profiles
      where id = auth.uid() and role = 'admin'
    )
  );

create policy "Service role has full access"
  on public.doctors for all
  using (auth.role() = 'service_role');

-- ----------------------------------------
-- Table: conversations
-- Chat sessions between patients and doctors (or AI).
-- ----------------------------------------
create table public.conversations (
  id uuid primary key default uuid_generate_v4(),
  patient_id uuid not null references public.patients(id) on delete cascade,
  doctor_id uuid references public.doctors(id) on delete set null,
  type text not null default 'ai' check (type in ('ai', 'human', 'hybrid')),
  status text not null default 'active' check (status in ('active', 'closed', 'escalated')),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

comment on table public.conversations is 'Conversation sessions. type: ai=AI-only, human=doctor-only, hybrid=both.';

create index idx_conversations_patient_id on public.conversations using btree (patient_id);
create index idx_conversations_doctor_id on public.conversations using btree (doctor_id);
create index idx_conversations_status on public.conversations using btree (status);
create index idx_conversations_type on public.conversations using btree (type);
create index idx_conversations_created_at on public.conversations using btree (created_at desc);

create trigger set_conversations_updated_at
  before update on public.conversations
  for each row execute procedure public.handle_updated_at();

alter table public.conversations enable row level security;

-- RLS: conversations
create policy "Patients can view their own conversations"
  on public.conversations for select
  using (
    patient_id in (
      select id from public.patients where user_id = auth.uid()
    )
  );

create policy "Doctors can view conversations assigned to them"
  on public.conversations for select
  using (
    doctor_id in (
      select id from public.doctors where user_id = auth.uid()
    )
  );

create policy "Patients can create conversations"
  on public.conversations for insert
  with check (
    patient_id in (
      select id from public.patients where user_id = auth.uid()
    )
  );

create policy "Doctors and patients can update their conversations"
  on public.conversations for update
  using (
    patient_id in (
      select id from public.patients where user_id = auth.uid()
    )
    or
    doctor_id in (
      select id from public.doctors where user_id = auth.uid()
    )
  );

create policy "Admins have full access"
  on public.conversations for all
  using (
    exists (
      select 1 from public.profiles
      where id = auth.uid() and role = 'admin'
    )
  );

create policy "Service role has full access"
  on public.conversations for all
  using (auth.role() = 'service_role');

-- ----------------------------------------
-- Table: messages
-- Individual messages within conversations.
-- ----------------------------------------
create table public.messages (
  id uuid primary key default uuid_generate_v4(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  sender_id uuid references public.profiles(id) on delete set null,
  sender_type text not null check (sender_type in ('patient', 'doctor', 'ai')),
  content text not null,
  message_type text not null default 'text' check (message_type in ('text', 'image', 'file', 'audio')),
  is_read boolean not null default false,
  created_at timestamptz not null default timezone('utc', now())
);

comment on table public.messages is 'Messages within conversations. sender_type indicates who sent the message.';

create index idx_messages_conversation_id on public.messages using btree (conversation_id);
create index idx_messages_sender_id on public.messages using btree (sender_id);
create index idx_messages_sender_type on public.messages using btree (sender_type);
create index idx_messages_created_at on public.messages using btree (created_at desc);
create index idx_messages_conversation_created on public.messages using btree (conversation_id, created_at desc);
create index idx_messages_content on public.messages using gin (to_tsvector('english', content));

alter table public.messages enable row level security;

-- RLS: messages
create policy "Participants can view messages in their conversations"
  on public.messages for select
  using (
    conversation_id in (
      select id from public.conversations
      where
        patient_id in (
          select id from public.patients where user_id = auth.uid()
        )
        or
        doctor_id in (
          select id from public.doctors where user_id = auth.uid()
        )
    )
  );

create policy "Participants can insert messages in their conversations"
  on public.messages for insert
  with check (
    conversation_id in (
      select id from public.conversations
      where
        patient_id in (
          select id from public.patients where user_id = auth.uid()
        )
        or
        doctor_id in (
          select id from public.doctors where user_id = auth.uid()
        )
    )
  );

create policy "Participants can update read status of messages"
  on public.messages for update
  using (
    conversation_id in (
      select id from public.conversations
      where
        patient_id in (
          select id from public.patients where user_id = auth.uid()
        )
        or
        doctor_id in (
          select id from public.doctors where user_id = auth.uid()
        )
    )
  )
  with check (
    conversation_id in (
      select id from public.conversations
      where
        patient_id in (
          select id from public.patients where user_id = auth.uid()
        )
        or
        doctor_id in (
          select id from public.doctors where user_id = auth.uid()
        )
    )
  );

create policy "Service role has full access"
  on public.messages for all
  using (auth.role() = 'service_role');

-- ----------------------------------------
-- Table: appointments
-- Scheduled appointments between patients and doctors.
-- ----------------------------------------
create table public.appointments (
  id uuid primary key default uuid_generate_v4(),
  patient_id uuid not null references public.patients(id) on delete cascade,
  doctor_id uuid not null references public.doctors(id) on delete cascade,
  scheduled_at timestamptz not null,
  duration_minutes int not null default 30 check (duration_minutes > 0 and duration_minutes <= 180),
  status text not null default 'pending' check (status in ('pending', 'confirmed', 'cancelled', 'completed')),
  notes text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  constraint unique_appointment_per_doctor_per_slot
    unique (doctor_id, scheduled_at)
);

comment on table public.appointments is 'Appointments between patients and doctors. Unique constraint prevents double-booking per doctor per time slot.';

create index idx_appointments_patient_id on public.appointments using btree (patient_id);
create index idx_appointments_doctor_id on public.appointments using btree (doctor_id);
create index idx_appointments_scheduled_at on public.appointments using btree (scheduled_at);
create index idx_appointments_status on public.appointments using btree (status);
create index idx_appointments_doctor_scheduled on public.appointments using btree (doctor_id, scheduled_at);
create index idx_appointments_patient_scheduled on public.appointments using btree (patient_id, scheduled_at desc);

create trigger set_appointments_updated_at
  before update on public.appointments
  for each row execute procedure public.handle_updated_at();

alter table public.appointments enable row level security;

-- RLS: appointments
create policy "Patients can view their own appointments"
  on public.appointments for select
  using (
    patient_id in (
      select id from public.patients where user_id = auth.uid()
    )
  );

create policy "Doctors can view their own appointments"
  on public.appointments for select
  using (
    doctor_id in (
      select id from public.doctors where user_id = auth.uid()
    )
  );

create policy "Patients can create appointments"
  on public.appointments for insert
  with check (
    patient_id in (
      select id from public.patients where user_id = auth.uid()
    )
  );

create policy "Doctors and patients can update their appointments"
  on public.appointments for update
  using (
    patient_id in (
      select id from public.patients where user_id = auth.uid()
    )
    or
    doctor_id in (
      select id from public.doctors where user_id = auth.uid()
    )
  )
  with check (
    patient_id in (
      select id from public.patients where user_id = auth.uid()
    )
    or
    doctor_id in (
      select id from public.doctors where user_id = auth.uid()
    )
  );

create policy "Admins have full access"
  on public.appointments for all
  using (
    exists (
      select 1 from public.profiles
      where id = auth.uid() and role = 'admin'
    )
  );

create policy "Service role has full access"
  on public.appointments for all
  using (auth.role() = 'service_role');

-- ----------------------------------------
-- Table: api_keys
-- Stores API keys for external integrations or AI services.
-- ----------------------------------------
create table public.api_keys (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references public.profiles(id) on delete cascade,
  key_name text not null,
  key_hash text not null,
  key_prefix text not null,
  is_active boolean not null default true,
  last_used_at timestamptz,
  expires_at timestamptz,
  created_at timestamptz not null default timezone('utc', now())
);

comment on table public.api_keys is 'API keys for users. Stores a hash of the key, never the plaintext.';

create index idx_api_keys_user_id on public.api_keys using btree (user_id);
create index idx_api_keys_key_prefix on public.api_keys using btree (key_prefix);
create index idx_api_keys_is_active on public.api_keys using btree (is_active);
create unique index idx_api_keys_unique_active_per_user
  on public.api_keys (user_id)
  where is_active = true;

alter table public.api_keys enable row level security;

-- RLS: api_keys
create policy "Users can view their own API keys"
  on public.api_keys for select
  using (user_id = auth.uid());

create policy "Users can insert their own API keys"
  on public.api_keys for insert
  with check (user_id = auth.uid());

create policy "Users can update their own API keys"
  on public.api_keys for update
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

create policy "Users can delete their own API keys"
  on public.api_keys for delete
  using (user_id = auth.uid());

create policy "Service role has full access"
  on public.api_keys for all
  using (auth.role() = 'service_role');

-- ----------------------------------------
-- Realtime Publication
-- Enable Supabase Realtime for selected tables.
-- ----------------------------------------
alter publication supabase_realtime add table public.messages;
alter publication supabase_realtime add table public.conversations;
alter publication supabase_realtime add table public.appointments;

-- ----------------------------------------
-- Helper Views (Optional)
-- ----------------------------------------

-- View: doctor_summary
-- Flattened doctor info with user profile data.
create or replace view public.doctor_summary as
select
  d.id,
  d.user_id,
  p.full_name,
  p.avatar_url,
  p.language,
  d.pmdc_number,
  d.specialization,
  d.bio,
  d.is_verified,
  d.is_available,
  d.rating,
  d.total_reviews,
  d.created_at
from public.doctors d
join public.profiles p on p.id = d.user_id
where p.is_active = true;

grant select on public.doctor_summary to authenticated;

-- View: patient_summary
-- Flattened patient info with user profile data.
create or replace view public.patient_summary as
select
  pt.id,
  pt.user_id,
  p.full_name,
  p.avatar_url,
  p.language,
  p.phone,
  pt.age,
  pt.gender,
  pt.medical_history,
  pt.assigned_doctor_id,
  pt.created_at
from public.patients pt
join public.profiles p on p.id = pt.user_id
where p.is_active = true;

grant select on public.patient_summary to authenticated;

-- View: appointment_summary
-- Appointment with patient and doctor names.
create or replace view public.appointment_summary as
select
  a.id,
  a.patient_id,
  a.doctor_id,
  p_patient.full_name as patient_name,
  p_doctor.full_name as doctor_name,
  a.scheduled_at,
  a.duration_minutes,
  a.status,
  a.notes,
  a.created_at
from public.appointments a
join public.patients pt on pt.id = a.patient_id
join public.doctors d on d.id = a.doctor_id
join public.profiles p_patient on p_patient.id = pt.user_id
join public.profiles p_doctor on p_doctor.id = d.user_id
where p_patient.is_active = true
  and p_doctor.is_active = true;

grant select on public.appointment_summary to authenticated;

-- ----------------------------------------
-- Functions: Helper utilities
-- ----------------------------------------

-- Function: get_user_role
-- Returns the role of the current authenticated user.
create or replace function public.get_user_role()
returns text as $$
begin
  return (
    select role from public.profiles
    where id = auth.uid()
    limit 1
  );
end;
$$ language plpgsql security definer;

-- Function: is_doctor_of_patient
-- Checks if the current user is the assigned doctor of a given patient.
create or replace function public.is_doctor_of_patient(p_patient_id uuid)
returns boolean as $$
begin
  return exists (
    select 1 from public.patients pt
    join public.doctors d on d.id = pt.assigned_doctor_id
    where pt.id = p_patient_id
      and d.user_id = auth.uid()
  );
end;
$$ language plpgsql security definer;

-- Function: can_access_conversation
-- Checks if the current user is a participant in a conversation.
create or replace function public.can_access_conversation(p_conversation_id uuid)
returns boolean as $$
begin
  return exists (
    select 1 from public.conversations c
    left join public.doctors d on d.id = c.doctor_id
    where c.id = p_conversation_id
      and (
        c.patient_id in (
          select id from public.patients where user_id = auth.uid()
        )
        or
        d.user_id = auth.uid()
      )
  );
end;
$$ language plpgsql security definer;

-- ----------------------------------------
-- Seed Data (Optional — for development only)
-- ----------------------------------------
-- Insert a demo patient user
-- Note: You must first create the user via Supabase Auth
-- (or use the service_role key to insert directly).

-- After creating auth users, you can seed profiles:
/*
insert into public.profiles (id, email, full_name, phone, role, language)
values
  ('00000000-0000-0000-0000-000000000001', 'demo@lopc.com', 'Demo Patient', '03001234567', 'patient', 'en'),
  ('00000000-0000-0000-0000-000000000002', 'dr.sarah@lopc.com', 'Dr. Sarah Ahmed', '03007654321', 'doctor', 'en'),
  ('00000000-0000-0000-0000-000000000003', 'admin@lopc.com', 'Admin User', '03009876543', 'admin', 'en')
on conflict (id) do nothing;

-- Seed doctors
insert into public.doctors (id, user_id, pmdc_number, specialization, bio, is_verified, is_available, rating)
values
  ('10000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002', 'PMDC-12345', 'Clinical Psychology', 'Experienced therapist specializing in anxiety and depression.', true, true, 4.85)
on conflict (id) do nothing;

-- Seed patients
insert into public.patients (id, user_id, age, gender, medical_history)
values
  ('20000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', 28, 'female', '{"conditions": ["anxiety"], "medications": ["none"]}')
on conflict (id) do nothing;
*/

-- ============================================================
-- End of Schema
-- ============================================================

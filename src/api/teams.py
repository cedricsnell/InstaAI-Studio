"""
Team Management API Routes for InstaAI Studio
Handles team creation, member management, and invitations
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import secrets

from ..database import get_db
from ..database.models import Team, TeamMember, TeamInvite, User, TeamRole, InviteStatus
from .auth import get_current_user

router = APIRouter(prefix="/teams", tags=["teams"])

# Request/Response Models
class TeamCreate(BaseModel):
    name: str
    description: Optional[str] = None
    max_members: int = 10

class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    max_members: Optional[int] = None
    is_active: Optional[bool] = None

class TeamResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    owner_id: int
    is_active: bool
    max_members: int
    subscription_tier: str
    created_at: datetime
    member_count: int

    class Config:
        from_attributes = True

class TeamMemberResponse(BaseModel):
    id: int
    user_id: int
    email: str
    full_name: str
    role: TeamRole
    can_manage_content: bool
    can_manage_instagram: bool
    can_view_analytics: bool
    can_invite_members: bool
    joined_at: datetime

    class Config:
        from_attributes = True

class TeamInviteCreate(BaseModel):
    email: EmailStr
    role: TeamRole = TeamRole.MEMBER
    can_manage_content: bool = True
    can_manage_instagram: bool = True
    can_view_analytics: bool = True

class TeamInviteResponse(BaseModel):
    id: int
    team_id: int
    team_name: str
    email: str
    role: TeamRole
    status: InviteStatus
    invited_by_email: str
    created_at: datetime
    expires_at: datetime
    token: Optional[str] = None  # Only included when creating the invite

    class Config:
        from_attributes = True


# Helper function to check team permissions
def check_team_permission(
    team: Team,
    user: User,
    db: Session,
    required_role: Optional[TeamRole] = None
) -> TeamMember:
    """Check if user has permission to access team."""
    member = db.query(TeamMember).filter(
        TeamMember.team_id == team.id,
        TeamMember.user_id == user.id
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this team"
        )

    if required_role:
        role_hierarchy = {
            TeamRole.VIEWER: 0,
            TeamRole.MEMBER: 1,
            TeamRole.ADMIN: 2,
            TeamRole.OWNER: 3
        }
        if role_hierarchy.get(member.role, 0) < role_hierarchy.get(required_role, 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role.value} role or higher"
            )

    return member


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_data: TeamCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new team."""
    # Create team
    team = Team(
        name=team_data.name,
        description=team_data.description,
        owner_id=current_user.id,
        max_members=team_data.max_members,
        subscription_tier=current_user.subscription_tier or 'free'
    )
    db.add(team)
    db.flush()

    # Add owner as team member
    owner_member = TeamMember(
        team_id=team.id,
        user_id=current_user.id,
        role=TeamRole.OWNER,
        can_manage_content=True,
        can_manage_instagram=True,
        can_view_analytics=True,
        can_invite_members=True
    )
    db.add(owner_member)
    db.commit()
    db.refresh(team)

    return TeamResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        owner_id=team.owner_id,
        is_active=team.is_active,
        max_members=team.max_members,
        subscription_tier=team.subscription_tier,
        created_at=team.created_at,
        member_count=1
    )


@router.get("", response_model=List[TeamResponse])
async def list_teams(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all teams the current user is a member of."""
    # Get all team memberships for the user
    memberships = db.query(TeamMember).filter(
        TeamMember.user_id == current_user.id
    ).all()

    teams = []
    for membership in memberships:
        team = membership.team
        member_count = db.query(TeamMember).filter(
            TeamMember.team_id == team.id
        ).count()

        teams.append(TeamResponse(
            id=team.id,
            name=team.name,
            description=team.description,
            owner_id=team.owner_id,
            is_active=team.is_active,
            max_members=team.max_members,
            subscription_tier=team.subscription_tier,
            created_at=team.created_at,
            member_count=member_count
        ))

    return teams


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get team details."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Check if user is a member
    check_team_permission(team, current_user, db)

    member_count = db.query(TeamMember).filter(
        TeamMember.team_id == team.id
    ).count()

    return TeamResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        owner_id=team.owner_id,
        is_active=team.is_active,
        max_members=team.max_members,
        subscription_tier=team.subscription_tier,
        created_at=team.created_at,
        member_count=member_count
    )


@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: int,
    team_data: TeamUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update team settings (requires ADMIN or OWNER role)."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Check if user has admin permissions
    check_team_permission(team, current_user, db, required_role=TeamRole.ADMIN)

    # Update fields
    if team_data.name is not None:
        team.name = team_data.name
    if team_data.description is not None:
        team.description = team_data.description
    if team_data.max_members is not None:
        team.max_members = team_data.max_members
    if team_data.is_active is not None:
        team.is_active = team_data.is_active

    team.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(team)

    member_count = db.query(TeamMember).filter(
        TeamMember.team_id == team.id
    ).count()

    return TeamResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        owner_id=team.owner_id,
        is_active=team.is_active,
        max_members=team.max_members,
        subscription_tier=team.subscription_tier,
        created_at=team.created_at,
        member_count=member_count
    )


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete team (requires OWNER role)."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Only owner can delete team
    if team.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only team owner can delete the team"
        )

    db.delete(team)
    db.commit()

    return None


@router.post("/{team_id}/invite", response_model=TeamInviteResponse, status_code=status.HTTP_201_CREATED)
async def send_team_invite(
    team_id: int,
    invite_data: TeamInviteCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send an invitation to join the team."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Check if user has permission to invite
    member = check_team_permission(team, current_user, db, required_role=TeamRole.ADMIN)
    if not member.can_invite_members and member.role not in [TeamRole.ADMIN, TeamRole.OWNER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to invite members"
        )

    # Check if user is already a member
    existing_member = db.query(TeamMember).join(User).filter(
        TeamMember.team_id == team_id,
        User.email == invite_data.email
    ).first()

    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a team member"
        )

    # Check for existing pending invite
    existing_invite = db.query(TeamInvite).filter(
        TeamInvite.team_id == team_id,
        TeamInvite.email == invite_data.email,
        TeamInvite.status == InviteStatus.PENDING
    ).first()

    if existing_invite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A pending invitation already exists for this email"
        )

    # Check team member limit
    current_member_count = db.query(TeamMember).filter(
        TeamMember.team_id == team_id
    ).count()

    if current_member_count >= team.max_members:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team has reached maximum member limit"
        )

    # Create invite token
    token = secrets.token_urlsafe(32)

    # Create invite
    invite = TeamInvite(
        team_id=team_id,
        email=invite_data.email,
        role=invite_data.role,
        invited_by_id=current_user.id,
        token=token,
        can_manage_content=invite_data.can_manage_content,
        can_manage_instagram=invite_data.can_manage_instagram,
        can_view_analytics=invite_data.can_view_analytics,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    return TeamInviteResponse(
        id=invite.id,
        team_id=invite.team_id,
        team_name=team.name,
        email=invite.email,
        role=invite.role,
        status=invite.status,
        invited_by_email=current_user.email,
        created_at=invite.created_at,
        expires_at=invite.expires_at,
        token=token  # Include token for sharing with invitee
    )


@router.post("/invites/{token}/accept", response_model=TeamMemberResponse)
async def accept_team_invite(
    token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Accept a team invitation."""
    invite = db.query(TeamInvite).filter(TeamInvite.token == token).first()

    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found")

    # Verify email matches current user
    if invite.email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invitation is for a different email address"
        )

    # Check if invite is still valid
    if invite.status != InviteStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invitation has already been {invite.status.value}"
        )

    if invite.expires_at < datetime.utcnow():
        invite.status = InviteStatus.EXPIRED
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation has expired"
        )

    # Check if already a member
    existing_member = db.query(TeamMember).filter(
        TeamMember.team_id == invite.team_id,
        TeamMember.user_id == current_user.id
    ).first()

    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a member of this team"
        )

    # Create team membership
    member = TeamMember(
        team_id=invite.team_id,
        user_id=current_user.id,
        role=invite.role,
        can_manage_content=invite.can_manage_content,
        can_manage_instagram=invite.can_manage_instagram,
        can_view_analytics=invite.can_view_analytics,
        can_invite_members=(invite.role in [TeamRole.ADMIN, TeamRole.OWNER])
    )
    db.add(member)

    # Update invite status
    invite.status = InviteStatus.ACCEPTED
    invite.accepted_at = datetime.utcnow()

    db.commit()
    db.refresh(member)

    return TeamMemberResponse(
        id=member.id,
        user_id=member.user_id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=member.role,
        can_manage_content=member.can_manage_content,
        can_manage_instagram=member.can_manage_instagram,
        can_view_analytics=member.can_view_analytics,
        can_invite_members=member.can_invite_members,
        joined_at=member.joined_at
    )


@router.post("/invites/{token}/decline", status_code=status.HTTP_204_NO_CONTENT)
async def decline_team_invite(
    token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Decline a team invitation."""
    invite = db.query(TeamInvite).filter(TeamInvite.token == token).first()

    if not invite:
        raise HTTPException(status_code=404, detail="Invitation not found")

    # Verify email matches current user
    if invite.email != current_user.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This invitation is for a different email address"
        )

    # Check if invite is still pending
    if invite.status != InviteStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invitation has already been {invite.status.value}"
        )

    # Update invite status
    invite.status = InviteStatus.DECLINED
    db.commit()

    return None


@router.get("/{team_id}/members", response_model=List[TeamMemberResponse])
async def list_team_members(
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all members of a team."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Check if user is a member
    check_team_permission(team, current_user, db)

    members = db.query(TeamMember).filter(TeamMember.team_id == team_id).all()

    result = []
    for member in members:
        user = db.query(User).filter(User.id == member.user_id).first()
        result.append(TeamMemberResponse(
            id=member.id,
            user_id=member.user_id,
            email=user.email,
            full_name=user.full_name,
            role=member.role,
            can_manage_content=member.can_manage_content,
            can_manage_instagram=member.can_manage_instagram,
            can_view_analytics=member.can_view_analytics,
            can_invite_members=member.can_invite_members,
            joined_at=member.joined_at
        ))

    return result


@router.get("/{team_id}/invites", response_model=List[TeamInviteResponse])
async def list_team_invites(
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all pending invitations for a team."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Check if user has admin permissions
    check_team_permission(team, current_user, db, required_role=TeamRole.ADMIN)

    invites = db.query(TeamInvite).filter(
        TeamInvite.team_id == team_id,
        TeamInvite.status == InviteStatus.PENDING
    ).all()

    result = []
    for invite in invites:
        invited_by = db.query(User).filter(User.id == invite.invited_by_id).first()
        result.append(TeamInviteResponse(
            id=invite.id,
            team_id=invite.team_id,
            team_name=team.name,
            email=invite.email,
            role=invite.role,
            status=invite.status,
            invited_by_email=invited_by.email if invited_by else "Unknown",
            created_at=invite.created_at,
            expires_at=invite.expires_at
        ))

    return result


@router.delete("/{team_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_team_member(
    team_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a member from the team (requires ADMIN or OWNER role)."""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Check if user has admin permissions
    check_team_permission(team, current_user, db, required_role=TeamRole.ADMIN)

    # Cannot remove the owner
    if user_id == team.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove team owner"
        )

    # Find the member to remove
    member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.user_id == user_id
    ).first()

    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")

    db.delete(member)
    db.commit()

    return None

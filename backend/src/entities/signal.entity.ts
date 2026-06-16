import {
  Column,
  Entity,
  JoinColumn,
  ManyToOne,
  PrimaryGeneratedColumn,
} from 'typeorm';
import { Bot } from './bot.entity';

@Entity('signals')
export class Signal {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column('text', { name: 'bot_id' })
  botId: string;

  @ManyToOne(() => Bot, (bot) => bot.signals)
  @JoinColumn({ name: 'bot_id' })
  bot: Bot;

  @Column('timestamptz', { nullable: true })
  time: Date | null;

  @Column('text', { nullable: true })
  direction: string | null;

  @Column('decimal', { nullable: true })
  confidence: string | null;

  @Column('jsonb', { name: 'ml_features', nullable: true })
  mlFeatures: Record<string, unknown> | null;

  @Column('text', { name: 'news_trigger', nullable: true })
  newsTrigger: string | null;

  @Column('boolean', { name: 'acted_on', default: false })
  actedOn: boolean;
}
